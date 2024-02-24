docker build -t python-worker python-worker/.
docker build -t nodejs-api node-app/.
pip install -r requirements.txt
docker-compose up --build  
python3 exercise-api.py
