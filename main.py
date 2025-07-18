import os
import uuid
import logging
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logger = logging.getLogger("CloudantAPI")
logging.basicConfig(level=logging.INFO)

class CloudantClient:
    def __init__(self, base_url: str, iam_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {iam_token}",
            "Content-Type": "application/json"
        }

    def create_database(self, db_name: str) -> dict:
        url = f"{self.base_url}/{db_name}"
        response = requests.put(url, headers=self.headers)
        if response.status_code == 201:
            return {"message": "Database created."}
        elif response.status_code == 412:
            return {"message": "Database already exists."}
        response.raise_for_status()

    def list_documents(self, db_name: str) -> dict:
        url = f"{self.base_url}/{db_name}/_all_docs?include_docs=true"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def add_document(self, db_name: str, document: dict) -> dict:
        url = f"{self.base_url}/{db_name}"
        response = requests.post(url, json=document, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_document(self, db_name: str, doc_id: str) -> dict:
        url = f"{self.base_url}/{db_name}/{doc_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def delete_document(self, db_name: str, doc_id: str, rev: str) -> dict:
        url = f"{self.base_url}/{db_name}/{doc_id}?rev={rev}"
        response = requests.delete(url, headers=self.headers)
        return response.json()


def get_iam_token(api_key: str) -> str:
    url = "https://iam.cloud.ibm.com/identity/token"
    data = {
        "apikey": api_key,
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    return response.json().get("access_token")


CLOUDANT_API_KEY = os.environ.get("CLOUDANT_API_KEY", "GTZP48e-lYy23sep8ZsRX7yonFLvrftrDfq-hFP5BfHZ")
CLOUDANT_SERVICE_URL = os.environ.get("CLOUDANT_SERVICE_URL", "https://293e9a3b-b044-4b74-a92a-3b331de2350a-bluemix.cloudantnosqldb.appdomain.cloud")
DB_NAME = os.environ.get("CLOUDANT_DB_NAME", "cloudant")


# Initialize Cloudant client
# try:
#     iam_token = get_iam_token(CLOUDANT_API_KEY)
#     cloudant_client = CloudantClient(CLOUDANT_SERVICE_URL, iam_token)
#     logger.info("Connected to Cloudant.")
#
#     # Ensure database exists
#     db_response = cloudant_client.create_database(DB_NAME)
#     logger.info(f"Database response: {db_response}")
# except Exception as e:
#     logger.error(f"Cloudant connection error: {e}", exc_info=True)
#     cloudant_client = None


@app.route("/documents", methods=["GET"])
def list_documents():
    iam_token = get_iam_token(CLOUDANT_API_KEY)
    logger.info("Connected to Cloudant.")

    try:
        cloudant_client = CloudantClient(CLOUDANT_SERVICE_URL, iam_token)
        logger.info("Connected to Cloudant.")
        response = cloudant_client.list_documents(DB_NAME)
        if "rows" in response:
            docs = [row["doc"] for row in response["rows"]]
            return jsonify(docs), 200
        return jsonify({"error": "Failed to list documents."}), 500

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return jsonify({"error": "Internal server error."}), 500


@app.route("/documents", methods=["POST"])
def create_document():
    if not cloudant_client:
        return jsonify({"error": "Database connection error."}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid payload"}), 400

        # Add a unique ID if not provided
        if "_id" not in data:
            data["_id"] = str(uuid.uuid4())

        response = cloudant_client.add_document(DB_NAME, data)
        if "ok" in response and response["ok"]:
            return jsonify({"message": "Document created successfully", "id": response["id"]}), 201
        else:
            return jsonify({"error": "Failed to create document", "details": response}), 500

    except Exception as e:
        logger.error(f"Error creating document: {e}")
        return jsonify({"error": "Internal server error."}), 500


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
        app.run(debug=True,host="0.0.0.0", port=5000)
    except Exception as e:
        logger.error(f"Application startup error: {e}")
