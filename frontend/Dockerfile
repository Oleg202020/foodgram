FROM node:21.7.1-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

CMD ["npx", "-y", "http-server", "-p", "8080", "/app/build"]
