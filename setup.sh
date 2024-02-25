docker build -t python-worker python-worker/.
docker build -t nodejs-api node-app/.
pip3 install -r requirements.txt
docker-compose up --build  
sleep 30
python3 exercise-api.py
