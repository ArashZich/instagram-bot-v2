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
    if item.get("_id"):
        item["id"] = str(item.pop("_id"))
    return item

# Helper for relative time


def get_relative_time(timestamp):
    """تبدیل timestamp به زمان نسبی (مثلاً '2 ساعت پیش')"""
    if not timestamp:
        return "نامشخص"

    now = datetime.now()
    diff = now - timestamp

    # ثانیه‌ها
    seconds = diff.total_seconds()

    if seconds < 60:
        return "چند لحظه پیش"

    # دقیقه‌ها
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"{minutes} دقیقه پیش"

    # ساعت‌ها
    hours = int(seconds / 3600)
    if hours < 24:
        return f"{hours} ساعت پیش"

    # روزها
    days = int(seconds / 86400)
    if days < 7:
        return f"{days} روز پیش"

    # هفته‌ها
    weeks = int(days / 7)
    if weeks < 4:
        return f"{weeks} هفته پیش"

    # ماه‌ها
    months = int(days / 30)
    if months < 12:
        return f"{months} ماه پیش"

    # سال‌ها
    years = int(days / 365)
    return f"{years} سال پیش"

# Database dependency


async def get_db():
    db = await get_async_database()
    return db


@app.get("/", tags=["Health"])
async def root():
    """API health check endpoint"""
    return {"status": "ok", "message": "Instagram Bot API is running"}


# Interactions endpoints with improved data
@app.get("/interactions/", tags=["Interactions"])
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
    """Get interactions with optional filtering and improved data"""
    query = {}

    if interaction_type:
        query["interaction_type"] = interaction_type

    if username:
        # جستجوی غیرحساس به حروف بزرگ و کوچک
        query["username"] = {'$regex': username, '$options': 'i'}

    if user_id:
        query["user_id"] = user_id

    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_query["$lte"] = datetime.fromisoformat(end_date)
        query["timestamp"] = date_query

    # Get total count for pagination
    total_count = await db[get_collection_name("interactions")].count_documents(query)

    cursor = db[get_collection_name("interactions")].find(
        query).sort("timestamp", -1).skip(skip).limit(limit)

    interactions = []
    async for doc in cursor:
        # Add relative time for better display
        doc["relative_time"] = get_relative_time(doc["timestamp"])
        interactions.append(convert_objectid(doc))

    return {
        "data": interactions,
        "total": total_count,
        "pages": (total_count + limit - 1) // limit if limit > 0 else 1,
        "page": (skip // limit) + 1 if limit > 0 else 1
    }


@app.get("/interactions/{interaction_id}", tags=["Interactions"])
async def get_interaction(
    interaction_id: str = Path(..., description="The ID of the interaction"),
    db=Depends(get_db)
):
    """Get a specific interaction by ID with more useful data"""
    try:
        doc = await db[get_collection_name("interactions")].find_one({"_id": ObjectId(interaction_id)})
        if not doc:
            raise HTTPException(
                status_code=404, detail="Interaction not found")

        # Add relative time
        doc["relative_time"] = get_relative_time(doc["timestamp"])

        # Add user information if available
        if doc.get("user_id"):
            user_info = await db[get_collection_name("users")].find_one({"user_id": doc["user_id"]})
            if user_info:
                doc["user_info"] = {
                    "full_name": user_info.get("full_name"),
                    "is_follower": user_info.get("is_follower", False),
                    "is_following": user_info.get("is_following", False),
                    "interaction_count": user_info.get("interaction_count", 0)
                }

        return convert_objectid(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Users endpoints with improved data
@app.get("/users/", tags=["Users"])
async def get_users(
    params: UserQueryParams = Depends(),
    db=Depends(get_db)
):
    """Get user profiles with more useful information"""
    query = {}

    if params.is_follower is not None:
        query["is_follower"] = params.is_follower

    if params.is_following is not None:
        query["is_following"] = params.is_following

    # Get total count for pagination
    total_count = await db[get_collection_name("users")].count_documents(query)

    cursor = db[get_collection_name("users")].find(query).sort(
        "last_interaction", -1).skip(params.skip).limit(params.limit)

    users = []
    async for doc in cursor:
        # Add relative time for last interaction
        if doc.get("last_interaction"):
            doc["relative_last_interaction"] = get_relative_time(
                doc["last_interaction"])

        # Add recent interaction count (7 days)
        recent_interactions_count = await db[get_collection_name("interactions")].count_documents({
            "user_id": doc["user_id"],
            "timestamp": {"$gte": datetime.now() - timedelta(days=7)}
        })
        doc["recent_interactions_count"] = recent_interactions_count

        users.append(convert_objectid(doc))

    return {
        "data": users,
        "total": total_count,
        "pages": (total_count + params.limit - 1) // params.limit if params.limit > 0 else 1,
        "page": (params.skip // params.limit) + 1 if params.limit > 0 else 1
    }


@app.get("/users/{user_id}", tags=["Users"])
async def get_user(
    user_id: str = Path(..., description="The user ID"),
    db=Depends(get_db)
):
    """Get a specific user profile with enhanced data"""
    doc = await db[get_collection_name("users")].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")

    # Add relative time for last interaction
    if doc.get("last_interaction"):
        doc["relative_last_interaction"] = get_relative_time(
            doc["last_interaction"])

    # Add interaction type distribution
    interaction_types_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$interaction_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    interaction_types_cursor = db[get_collection_name(
        "interactions")].aggregate(interaction_types_pipeline)

    interaction_types = {}
    async for type_doc in await interaction_types_cursor.to_list(length=10):
        interaction_types[type_doc["_id"]] = type_doc["count"]

    doc["interaction_types"] = interaction_types

    # Add 5 most recent interactions
    recent_interactions_cursor = db[get_collection_name("interactions")].find(
        {"user_id": user_id}
    ).sort("timestamp", -1).limit(5)

    recent_interactions = []
    async for interaction in await recent_interactions_cursor.to_list(length=5):
        interaction["relative_time"] = get_relative_time(
            interaction["timestamp"])
        recent_interactions.append(convert_objectid(interaction))

    doc["recent_interactions"] = recent_interactions

    return convert_objectid(doc)


@app.get("/users/{user_id}/interactions", tags=["Users"])
async def get_user_interactions(
    user_id: str = Path(..., description="The user ID"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    interaction_type: Optional[str] = None,
    db=Depends(get_db)
):
    """Get all interactions for a specific user with enhanced data"""
    query = {"user_id": user_id}

    if interaction_type:
        query["interaction_type"] = interaction_type

    # Count total for pagination
    total_count = await db[get_collection_name("interactions")].count_documents(query)

    cursor = db[get_collection_name("interactions")].find(
        query
    ).sort("timestamp", -1).skip(skip).limit(limit)

    interactions = []
    async for doc in cursor:
        # Add relative time
        doc["relative_time"] = get_relative_time(doc["timestamp"])
        interactions.append(convert_objectid(doc))

    return {
        "data": interactions,
        "total": total_count,
        "pages": (total_count + limit - 1) // limit if limit > 0 else 1,
        "page": (skip // limit) + 1 if limit > 0 else 1
    }


# Enhanced Statistics endpoint
@app.get("/stats", tags=["Statistics"])
async def get_stats(
    params: StatsQueryParams = Depends(),
    db=Depends(get_db)
):
    """Get enriched bot statistics for the specified time range"""
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

    async for doc in await interaction_cursor.to_list(length=10):
        count = doc["count"]
        interaction_types.append(InteractionCount(
            interaction_type=doc["_id"],
            count=count
        ))
        total_interactions += count

    # Get time series data with better granularity
    time_format = "%Y-%m-%d"
    if params.time_range == TimeRange.DAILY:
        time_format = "%Y-%m-%d %H:00"  # Hourly for daily view
    elif params.time_range == TimeRange.WEEKLY:
        time_format = "%Y-%m-%d"  # Daily for weekly view
    elif params.time_range == TimeRange.YEARLY:
        time_format = "%Y-%m"  # Monthly for yearly view

    time_series_pipeline = [
        {"$match": {"timestamp": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": time_format, "date": "$timestamp"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]

    time_series_cursor = db[get_collection_name(
        "interactions")].aggregate(time_series_pipeline)

    time_series = []
    async for doc in await time_series_cursor.to_list(length=100):
        time_series.append(TimeSeriesPoint(
            date=doc["_id"],
            count=doc["count"]
        ))

    # Get user stats with additional data
    total_users = await db[get_collection_name("users")].count_documents({})
    followers_count = await db[get_collection_name("users")].count_documents({"is_follower": True})
    following_count = await db[get_collection_name("users")].count_documents({"is_following": True})
    new_users_count = await db[get_collection_name("users")].count_documents(
        {"first_seen": {"$gte": start_date, "$lte": end_date}}
    )

    # Get follow/unfollow counts
    new_follows = await db[get_collection_name("interactions")].count_documents({
        "interaction_type": "follow",
        "timestamp": {"$gte": start_date, "$lte": end_date}
    })

    unfollows = await db[get_collection_name("interactions")].count_documents({
        "interaction_type": "unfollow",
        "timestamp": {"$gte": start_date, "$lte": end_date}
    })

    # Get most interacted users with enhanced data
    most_interacted_pipeline = [
        {"$sort": {"interaction_count": -1}},
        {"$limit": params.limit}
    ]

    most_interacted_cursor = db[get_collection_name(
        "users")].aggregate(most_interacted_pipeline)

    most_interacted = []
    async for doc in await most_interacted_cursor.to_list(length=params.limit):
        # Add last interaction time in relative format
        if doc.get("last_interaction"):
            doc["relative_last_interaction"] = get_relative_time(
                doc["last_interaction"])

        # Get main interaction type
        user_id = doc["user_id"]
        main_interaction_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$interaction_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]

        main_interaction_result = await db[get_collection_name("interactions")].aggregate(main_interaction_pipeline).to_list(length=1)
        if main_interaction_result:
            doc["main_interaction_type"] = main_interaction_result[0]["_id"]

        most_interacted.append(convert_objectid(doc))

    # Get bot stats with improved runtime calculation
    session_count = await db[get_collection_name("sessions")].count_documents({})
    active_session = await db[get_collection_name("sessions")].find_one(
        {"is_active": True},
        sort=[("started_at", -1)]
    )

    last_session = await db[get_collection_name("sessions")].find_one(
        sort=[("started_at", -1)]
    )

    # Better runtime format
    runtime_pipeline = [
        {"$match": {"ended_at": {"$exists": True}}},
        {"$project": {
            "duration": {"$subtract": ["$ended_at", "$started_at"]}
        }},
        {"$group": {"_id": None, "total_duration": {"$sum": "$duration"}}}
    ]

    runtime_result = await db[get_collection_name("sessions")].aggregate(runtime_pipeline).to_list(length=1)

    total_runtime = "0 hours"
    if runtime_result and len(runtime_result) > 0:
        # Convert from milliseconds with better format
        total_seconds = runtime_result[0]["total_duration"] / 1000
        hours = int(total_seconds / 3600)
        minutes = int((total_seconds % 3600) / 60)
        total_runtime = f"{hours} ساعت و {minutes} دقیقه"

    # Calculate period runtime
    period_runtime_pipeline = [
        {"$match": {
            "$or": [
                {"started_at": {"$gte": start_date, "$lte": end_date}},
                {"ended_at": {"$gte": start_date, "$lte": end_date}}
            ]
        }},
        {"$project": {
            "start": {"$max": ["$started_at", start_date]},
            "end": {"$min": [{"$ifNull": ["$ended_at", end_date]}, end_date]}
        }},
        {"$project": {
            "duration": {"$subtract": ["$end", "$start"]}
        }},
        {"$group": {"_id": None, "total_duration": {"$sum": "$duration"}}}
    ]

    period_runtime_result = await db[get_collection_name("sessions")].aggregate(period_runtime_pipeline).to_list(length=1)

    period_runtime = "0 hours"
    if period_runtime_result and len(period_runtime_result) > 0:
        period_seconds = period_runtime_result[0]["total_duration"] / 1000
        hours = int(period_seconds / 3600)
        minutes = int((period_seconds % 3600) / 60)
        period_runtime = f"{hours} ساعت و {minutes} دقیقه"

    # Combine stats with enriched data
    return {
        "interactions": {
            "total_interactions": total_interactions,
            "interaction_types": interaction_types,
            "time_series": time_series,
            "hourly_rate": round(total_interactions / ((end_date - start_date).total_seconds() / 3600), 2) if (end_date - start_date).total_seconds() > 0 else 0
        },
        "users": {
            "total_users": total_users,
            "followers_count": followers_count,
            "following_count": following_count,
            "new_users_count": new_users_count,
            "most_interacted": most_interacted,
            "follows_unfollows": {
                "new_follows": new_follows,
                "unfollows": unfollows,
                "net_change": new_follows - unfollows
            },
            "ratio": {
                "followers_following": round(followers_count / following_count, 2) if following_count > 0 else 0
            }
        },
        "bot": {
            "total_runtime": total_runtime,
            "period_runtime": period_runtime,
            "session_count": session_count,
            "period_sessions": await db[get_collection_name("sessions")].count_documents({
                "started_at": {"$gte": start_date, "$lte": end_date}
            }),
            "last_session": last_session["started_at"] if last_session else None,
            "last_session_relative": get_relative_time(last_session["started_at"]) if last_session else "هرگز",
            "is_active": active_session is not None
        },
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": (end_date - start_date).days
        }
    }


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
