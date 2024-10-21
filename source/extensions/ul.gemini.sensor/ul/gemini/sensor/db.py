import asyncio
import ul.gemini.services.artifact_services as artifact_services
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from .utils import get_kafka_topic


partner_secure_data = artifact_services.get_partner_secure_data()
collection = get_kafka_topic(partner_secure_data)
uri = "mongodb+srv://AnyoneClown:s9640uXwVgAXCCrM@cluster0.9onnpny.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
async_client = AsyncIOMotorClient(uri, server_api=ServerApi("1"))
devices = async_client["testdb"][collection]


async def ping_and_aggregate():
    """
    This function pings the MongoDB deployment and aggregates the latest readings for each device.
    Returns:

    """

    try:
        await async_client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

    pipeline = [
        {
            "$sort": {
                "_id": -1,
            }
        },
        {
            "$group": {
                "_id": "$device_id",
                "latestReading": {
                    "$first": "$$ROOT",
                },
            }
        },
        {
            "$replaceRoot": {
                "newRoot": "$latestReading",
            }
        },
    ]

    try:
        cursor = devices.aggregate(pipeline)
        latest_readings = await cursor.to_list(length=None)
        return latest_readings
    except Exception as e:
        print(f"An error occurred during aggregation: {e}")
