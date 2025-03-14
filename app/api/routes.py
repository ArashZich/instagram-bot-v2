from fastapi import FastAPI, Query, Path, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import motor.motor_asyncio
import asyncio
from bson import ObjectId
import json

from app.config import MONGO_URI, MONGO_DB, API_HOST, API_PORT
from app.database.connection import get_async_database
from app.database.models import get_collection_name, InteractionType
from app.api.schemas import (
    InteractionResponse,
    UserProfileResponse,
    StatsResponse,
    InteractionStats,
    UserStats,
    BotStats,
    InteractionCount,
    TimeSeriesPoint,
    TimeRange,
    StatsQueryParams,
    UserQueryParams
)

# Create FastAPI app
app = FastAPI(
    title="Instagram Bot API",
    description="API for monitoring and controlling the Instagram Bot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper for MongoDB document conversion


def convert_objectid(item):
    """Convert MongoDB ObjectId to string in document"""
    result = {}

    try:
        for key, value in item.items():
            # تبدیل _id به id
            if key == "_id":
                result["id"] = str(value)
                continue

            # تبدیل تاریخ‌ها به رشته
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            # تبدیل اشیاء تودرتو
            elif isinstance(value, dict):
                result[key] = convert_objectid(value)
            # تبدیل لیست‌ها
            elif isinstance(value, list):
                result[key] = [convert_objectid(i) if isinstance(
                    i, dict) else i for i in value]
            # سایر موارد
            else:
                result[key] = value
    except Exception as e:
        print(f"Error in convert_objectid: {e}")
        # بازگشت آیتم اصلی در صورت خطا
        if isinstance(item, dict) and "_id" in item:
            item["id"] = str(item.pop("_id"))
        return item

    return result

# Database dependency


async def get_db():
    db = await get_async_database()
    return db


@app.get("/", tags=["Health"])
async def root():
    """API health check endpoint"""
    return {"status": "ok", "message": "Instagram Bot API is running"}

# Interactions endpoints


@app.get("/interactions/", response_model=List[InteractionResponse], tags=["Interactions"])
async def get_interactions(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    interaction_type: Optional[str] = None,
    username: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db=Depends(get_db)
):
    """Get interactions with optional filtering"""
    try:
        # ایجاد کوئری برای فیلتر کردن نتایج
        query = {}

        if interaction_type:
            query["interaction_type"] = interaction_type

        if username:
            query["username"] = username

        if user_id:
            query["user_id"] = user_id

        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_query["$lte"] = datetime.fromisoformat(end_date)
            query["timestamp"] = date_query

        # دریافت نام کالکشن صحیح
        collection_name = get_collection_name("interactions")
        print(f"Querying collection: {collection_name}")

        # بررسی وجود کالکشن
        collections = await db.list_collection_names()
        if collection_name not in collections:
            print(
                f"Collection {collection_name} not found! Available collections: {collections}")
            return []

        # لاگ کوئری
        print(f"Query: {query}")

        # جستجو در دیتابیس
        cursor = db[collection_name].find(
            query).sort("timestamp", -1).skip(skip).limit(limit)

        interactions = []
        async for doc in cursor:
            try:
                # لاگ داک‌ها برای دیباگ
                print(f"Found document: {doc}")

                # تنظیم ساختار داده‌ها برای انطباق با مدل پاسخ
                # برخی فیلدها ممکن است نیاز به پردازش داشته باشند
                # به عنوان مثال تبدیل InteractionType.STORY_REACTION به STORY_REACTION
                if "interaction_type" in doc and isinstance(doc["interaction_type"], str):
                    # حذف پیشوند InteractionType. اگر وجود داشته باشد
                    if doc["interaction_type"].startswith("InteractionType."):
                        doc["interaction_type"] = doc["interaction_type"].replace(
                            "InteractionType.", "")

                # اطمینان از وجود تمام فیلدهای مورد نیاز
                if "status" not in doc:
                    doc["status"] = "success"

                # تبدیل objectid و افزودن به لیست
                processed_doc = convert_objectid(doc)
                interactions.append(processed_doc)
            except Exception as doc_error:
                print(f"Error processing document: {doc_error}")
                # ادامه با سند بعدی

        return interactions
    except Exception as e:
        print(f"Error in get_interactions: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get("/interactions/{interaction_id}", response_model=InteractionResponse, tags=["Interactions"])
async def get_interaction(
    interaction_id: str = Path(..., description="The ID of the interaction"),
    db=Depends(get_db)
):
    """Get a specific interaction by ID"""
    try:
        doc = await db[get_collection_name("interactions")].find_one({"_id": ObjectId(interaction_id)})
        if not doc:
            raise HTTPException(
                status_code=404, detail="Interaction not found")
        return convert_objectid(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Users endpoints


@app.get("/users/", response_model=List[UserProfileResponse], tags=["Users"])
async def get_users(
    params: UserQueryParams = Depends(),
    db=Depends(get_db)
):
    """Get user profiles with optional filtering"""
    query = {}

    if params.is_follower is not None:
        query["is_follower"] = params.is_follower

    if params.is_following is not None:
        query["is_following"] = params.is_following

    cursor = db[get_collection_name("users")].find(query).sort(
        "last_interaction", -1).skip(params.skip).limit(params.limit)

    users = []
    async for doc in cursor:
        users.append(convert_objectid(doc))

    return users


@app.get("/users/{user_id}", response_model=UserProfileResponse, tags=["Users"])
async def get_user(
    user_id: str = Path(..., description="The user ID"),
    db=Depends(get_db)
):
    """Get a specific user profile"""
    doc = await db[get_collection_name("users")].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return convert_objectid(doc)


@app.get("/users/{user_id}/interactions", response_model=List[InteractionResponse], tags=["Users"])
async def get_user_interactions(
    user_id: str = Path(..., description="The user ID"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db=Depends(get_db)
):
    """Get all interactions for a specific user"""
    cursor = db[get_collection_name("interactions")].find(
        {"user_id": user_id}
    ).sort("timestamp", -1).skip(skip).limit(limit)

    interactions = []
    async for doc in cursor:
        interactions.append(convert_objectid(doc))

    return interactions

# Statistics endpoints


@app.get("/stats", response_model=StatsResponse, tags=["Statistics"])
async def get_stats(
    params: StatsQueryParams = Depends(),
    db=Depends(get_db)
):
    """Get bot statistics for the specified time range"""
    # Calculate start date based on time range
    end_date = datetime.now()

    if params.time_range == TimeRange.DAILY:
        start_date = end_date - timedelta(days=1)
    elif params.time_range == TimeRange.WEEKLY:
        start_date = end_date - timedelta(weeks=1)
    elif params.time_range == TimeRange.MONTHLY:
        start_date = end_date - timedelta(days=30)
    elif params.time_range == TimeRange.SIX_MONTHS:
        start_date = end_date - timedelta(days=180)
    elif params.time_range == TimeRange.YEARLY:
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(weeks=1)  # Default to weekly

    # Get interaction stats
    interaction_pipeline = [
        {"$match": {"timestamp": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {"_id": "$interaction_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    interaction_cursor = db[get_collection_name(
        "interactions")].aggregate(interaction_pipeline)

    interaction_types = []
    total_interactions = 0

    async for doc in interaction_cursor:
        count = doc["count"]
        interaction_types.append(InteractionCount(
            interaction_type=doc["_id"],
            count=count
        ))
        total_interactions += count

    # Get time series data (daily counts)
    time_series_pipeline = [
        {"$match": {"timestamp": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]

    time_series_cursor = db[get_collection_name(
        "interactions")].aggregate(time_series_pipeline)

    time_series = []
    async for doc in time_series_cursor:
        time_series.append(TimeSeriesPoint(
            date=doc["_id"],
            count=doc["count"]
        ))

    # Get user stats
    total_users = await db[get_collection_name("users")].count_documents({})
    followers_count = await db[get_collection_name("users")].count_documents({"is_follower": True})
    following_count = await db[get_collection_name("users")].count_documents({"is_following": True})
    new_users_count = await db[get_collection_name("users")].count_documents(
        {"first_seen": {"$gte": start_date, "$lte": end_date}}
    )

    # Get most interacted users
    most_interacted_pipeline = [
        {"$sort": {"interaction_count": -1}},
        {"$limit": params.limit}
    ]

    most_interacted_cursor = db[get_collection_name(
        "users")].aggregate(most_interacted_pipeline)

    most_interacted = []
    async for doc in most_interacted_cursor:
        most_interacted.append(convert_objectid(doc))

    # Get bot stats
    session_count = await db[get_collection_name("sessions")].count_documents({})
    active_session = await db[get_collection_name("sessions")].find_one(
        {"is_active": True},
        sort=[("started_at", -1)]
    )

    last_session = await db[get_collection_name("sessions")].find_one(
        sort=[("started_at", -1)]
    )

    # Calculate total runtime
    runtime_pipeline = [
        {"$match": {"ended_at": {"$exists": True}}},
        {"$project": {
            "duration": {"$subtract": ["$ended_at", "$started_at"]}
        }},
        {"$group": {"_id": None, "total_duration": {"$sum": "$duration"}}}
    ]

    runtime_result = await db[get_collection_name("sessions")].aggregate(runtime_pipeline).to_list(1)

    total_runtime = "0 hours"
    if runtime_result and len(runtime_result) > 0:
        # Convert from milliseconds
        total_seconds = runtime_result[0]["total_duration"] / 1000
        hours = int(total_seconds / 3600)
        total_runtime = f"{hours} hours"

    # Combine stats
    return StatsResponse(
        interactions=InteractionStats(
            total_interactions=total_interactions,
            interaction_types=interaction_types,
            time_series=time_series
        ),
        users=UserStats(
            total_users=total_users,
            followers_count=followers_count,
            following_count=following_count,
            new_users_count=new_users_count,
            most_interacted=most_interacted
        ),
        bot=BotStats(
            total_runtime=total_runtime,
            session_count=session_count,
            last_session=last_session["started_at"] if last_session else None,
            is_active=active_session is not None
        )
    )

# Bot control endpoints


@app.post("/bot/start", tags=["Bot Control"])
async def start_bot():
    """Start the Instagram bot (placeholder - bot runs in separate process)"""
    # This is just a placeholder since the bot runs in a separate container
    return {"status": "success", "message": "Bot start command sent"}


@app.post("/bot/stop", tags=["Bot Control"])
async def stop_bot():
    """Stop the Instagram bot (placeholder - bot runs in separate process)"""
    # This is just a placeholder since the bot runs in a separate container
    return {"status": "success", "message": "Bot stop command sent"}
