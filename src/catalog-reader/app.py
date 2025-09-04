from flask import Flask, jsonify, request
import os
import grpc
from google.protobuf.json_format import MessageToDict

# The PYTHONPATH is set in the Dockerfile, so we can import directly
from genproto import demo_pb2, demo_pb2_grpc

app = Flask(__name__)

# Environment variables for the gRPC services
PRODUCT_CATALOG_SERVICE_ADDR = os.environ.get('PRODUCT_CATALOG_SERVICE_ADDR', 'productcatalogservice:3550')

def get_product_catalog_stub():
    """Creates and returns a gRPC stub for the ProductCatalogService."""
    channel = grpc.insecure_channel(PRODUCT_CATALOG_SERVICE_ADDR)
    stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
    return stub

@app.route('/products', methods=['GET'])
def list_products():
    """Lists all products from the ProductCatalogService."""
    try:
        stub = get_product_catalog_stub()
        response = stub.ListProducts(demo_pb2.Empty())
        # Convert protobuf message to a dictionary for JSON serialization
        products = [MessageToDict(p) for p in response.products]
        return jsonify(products)
    except grpc.RpcError as e:
        return jsonify({"error": f"gRPC call failed: {e.details()}"}), 500


@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """Gets a single product by its ID."""
    try:
        stub = get_product_catalog_stub()
        request_message = demo_pb2.GetProductRequest(id=product_id)
        response = stub.GetProduct(request_message)
        return jsonify(MessageToDict(response))
    except grpc.RpcError as e:
        # Handle cases where the product is not found, or other gRPC errors
        if e.code() == grpc.StatusCode.NOT_FOUND:
            return jsonify({"error": "Product not found"}), 404
        return jsonify({"error": f"gRPC call failed: {e.details()}"}), 500


@app.route('/products:search', methods=['POST'])
def search_products():
    """Searches for products based on a query."""
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "JSON body with 'query' field is required."}), 400

    query = data['query']
    try:
        stub = get_product_catalog_stub()
        request_message = demo_pb2.SearchProductsRequest(query=query)
        response = stub.SearchProducts(request_message)
        results = [MessageToDict(r) for r in response.results]
        return jsonify(results)
    except grpc.RpcError as e:
        return jsonify({"error": f"gRPC call failed: {e.details()}"}), 500


if __name__ == '__main__':
    # Running in debug mode for development is fine,
    # but for production, a proper WSGI server like gunicorn is used (as in the Dockerfile).
    app.run(host='0.0.0.0', port=8080, debug=True)
