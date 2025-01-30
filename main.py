from flask import Flask, request, jsonify
from cloudant import Cloudant
import os
import uuid
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLOUDANT_API_KEY = os.environ.get("CLOUDANT_API_KEY", "your-api-key")
CLOUDANT_SERVICE_URL = os.environ.get("CLOUDANT_SERVICE_URL", "https://293e9a3b-b044-4b74-a92a-3b331de2350a-bluemix.cloudantnosqldb.appdomain.cloud")
DB_NAME = os.environ.get("CLOUDANT_DB_NAME", "cloudant")


db = None
if CLOUDANT_API_KEY and CLOUDANT_SERVICE_URL:
    try:
        client = Cloudant.iam(None, CLOUDANT_API_KEY, url=CLOUDANT_SERVICE_URL)
        client.connect()
        db = client.create_database(DB_NAME) if DB_NAME not in client.all_dbs() else client[DB_NAME]
        logger.info(f"Database '{DB_NAME}' successfully connected.")

        # Debugging and test data insertion
        if db.doc_count() == 0:
            logger.warning("No documents found in the database. Inserting a test document.")
            db.create_document({
                '_id': str(uuid.uuid4()),
                'name': 'Test Document',
                'timestamp': '2025-01-30'
            })
            logger.info("Test document inserted.")

    except Exception as e:
        logger.error(f"Cloudant connection error: {e}")
else:
    logger.error("Environment variables CLOUDANT_API_KEY and CLOUDANT_SERVICE_URL are required.")


@app.route("/documents", methods=["GET"])
def list_documents():
    if not db:
        return jsonify({"error": "Database connection error."}), 500

    try:
        docs = [doc for doc in db]
        return jsonify(docs), 200
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return jsonify({"error": "Internal server error."}), 500


@app.route("/documents", methods=["POST"])
def create_document():
    if not db:
        return jsonify({"error": "Database connection error."}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid payload"}), 400

        # Add a unique ID if not provided
        if "_id" not in data:
            data["_id"] = str(uuid.uuid4())

        doc = db.create_document(data)
        if doc.exists():
            return jsonify({"message": "Document created successfully", "id": doc['_id']}), 201
        else:
            return jsonify({"error": "Failed to create document"}), 500

    except Exception as e:
        logger.error(f"Error creating document: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/documents/<doc_id>", methods=["GET"])
def get_document(doc_id):
    if not db:
        return jsonify({"error": "Database connection error."}), 500

    try:
        doc = db[doc_id] if doc_id in db else None
        if not doc:
            return jsonify({"error": "Document not found."}), 404
        return jsonify(doc), 200
    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        return jsonify({"error": "Internal server error."}), 500


@app.route("/documents/<doc_id>", methods=["PUT"])
def update_document(doc_id):
    if not db:
        return jsonify({"error": "Database connection error."}), 500

    try:
        if doc_id not in db:
            return jsonify({"error": "Document not found."}), 404

        updated_data = request.json
        doc = db[doc_id]

        for key, value in updated_data.items():
            doc[key] = value

        doc.save()
        return jsonify({"message": "Document updated successfully.", "document": doc}), 200
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        return jsonify({"error": "Internal server error."}), 500


@app.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    if not db:
        return jsonify({"error": "Database connection error."}), 500

    try:
        if doc_id not in db:
            return jsonify({"error": "Document not found."}), 404

        doc = db[doc_id]
        doc.delete()
        return jsonify({"message": "Document deleted successfully."}), 200
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return jsonify({"error": "Internal server error."}), 500

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logger.error(f"Application startup error: {e}")
