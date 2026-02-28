docker run -d   --name ai-tutor-backend   -p 8000:8000   --restart unless-stopped   aitutor-image
docker stop ai-tutor-backend
docker rm ai-tutor-backend
docker build -t aitutor-image .

docker build -t ai-tutor-frontend-image .

docker run -d   --name ai-tutor-frontend   -p 3000:3000   --restart unless-stopped   ai-tutor-frontend-image

docker stop ai-tutor-frontend

docker stop ai-tutor-backend
docker rm ai-tutor-frontend

docker stop ai-tutor-frontend
docker rm ai-tutor-frontend



change_this_admin_registration_key


echo "# AITutor" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/anamul94/AITutor.git
git push -u origin main

git remote add origin https://github.com/anamul94/AITutor.git
git branch -M main
git push -u origin main