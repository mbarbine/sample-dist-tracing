import argparse
import time
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup basic logging
logging.basicConfig(filename='load_test.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

parser = argparse.ArgumentParser(description="API Load Testing Script")
parser.add_argument('--url', default="http://localhost:3000/", help="URL of the Node.js API")
parser.add_argument('--requests', type=int, default=1000, help="Number of requests to send")
parser.add_argument('--workers', type=int, default=20, help="Number of concurrent workers")
parser.add_argument('--rate_limit', type=float, default=0.1, help="Time in seconds between requests to avoid rate limiting")
args = parser.parse_args()

def send_request(url, request_type="GET", payload=None, i=0):
    """Send a single API request and return the response details."""
    try:
        start_time = time.time()
        headers = {"Content-Type": "application/json"} if request_type == "POST" else {}
        if request_type == "GET":
            response = requests.get(url, headers=headers)
        elif request_type == "POST":
            response = requests.post(url, json=payload, headers=headers)
        elapsed_time = time.time() - start_time

        if response.status_code in [200, 201]:
            logging.info(f"Request {i}: Type {request_type}, Status Code {response.status_code}, Time {elapsed_time:.2f} seconds")
            return f"Request {i}: Type {request_type}, Status Code {response.status_code}, Time {elapsed_time:.2f} seconds"
        else:
            logging.error(f"Request {i}: Type {request_type}, Error with Status Code {response.status_code}")
            return f"Request {i}: Type {request_type}, Error with Status Code {response.status_code}"
    except requests.exceptions.RequestException as e:
        logging.error(f"Request {i}: Type {request_type}, Request failed with exception {e}")
        return f"Request {i}: Type {request_type}, Request failed with exception {e}"

def main():
    print(f"Sending {args.requests} requests to {args.url} with {args.workers} workers at a rate limit of {args.rate_limit} seconds/request")
    logging.info(f"Starting load test: {args.requests} requests to {args.url} with {args.workers} workers")
    
    payloads = [{"data": f"Payload {i}"} for i in range(args.requests // 2)]  # Example payloads for POST requests
    
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for i in range(args.requests // 2):
            futures.append(executor.submit(send_request, args.url, "GET", i=i))
            time.sleep(args.rate_limit)  # Rate limiting
        for i, payload in enumerate(payloads):
            futures.append(executor.submit(send_request, args.url, "POST", payload=payload, i=i + args.requests // 2))
            time.sleep(args.rate_limit)  # Rate limiting
        
        for future in as_completed(futures):
            results.append(future.result())

    # Logging results
    for result in results:
        print(result)

if __name__ == "__main__":
    main()
