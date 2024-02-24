import argparse
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

parser = argparse.ArgumentParser(description="API Load Testing Script")
parser.add_argument('--url', default="http://localhost:3000/", help="URL of the Node.js API")
parser.add_argument('--requests', type=int, default=1000, help="Number of requests to send")
parser.add_argument('--workers', type=int, default=20, help="Number of concurrent workers")
args = parser.parse_args()

def send_request(url, request_type="GET", payload=None, i=0):
    """Send a single API request and return the response details."""
    try:
        start_time = time.time()
        if request_type == "GET":
            response = requests.get(url)
        elif request_type == "POST":
            response = requests.post(url, json=payload)
        # Add other request types as needed (PUT, DELETE, etc.)
        elapsed_time = time.time() - start_time
        # Basic validation of response status code (can be extended)
        if response.status_code in [200, 201]:
            return f"Request {i}: Type {request_type}, Status Code {response.status_code}, Time {elapsed_time:.2f} seconds"
        else:
            return f"Request {i}: Type {request_type}, Error with Status Code {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Request {i}: Type {request_type}, Request failed with exception {e}"

def main():
    print(f"Sending {args.requests} requests to {args.url}")
    
    # Mathpix tracing test!  payloads for POST requests (can be customized)
    payloads = [{"data": "Mathpix tracing test! 1"}, {"data": "Mathpix tracing test! 2"}]
    
    # Use ThreadPoolExecutor to send requests in parallel
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # tracing test!  of diversifying request types
        future_to_request = {executor.submit(send_request, args.url, "GET", i=i): i for i in range(args.requests // 2)}
        future_to_request.update({executor.submit(send_request, args.url, "POST", payload=payloads[i % len(payloads)], i=i+args.requests // 2): i for i in range(args.requests // 2)})

        for future in as_completed(future_to_request):
            request_id = future_to_request[future]
            try:
                result = future.result()
                print(result)
            except Exception as exc:
                print(f"Request {request_id} generated an exception: {exc}")

if __name__ == "__main__":
    main()

