FROM node:20-alpine AS build

ARG MIRROR=international
ARG VITE_NODE_API_URL=/api
ARG VITE_PY_API_URL=/py
# 国内构建: docker build --build-arg MIRROR=china .

ENV VITE_NODE_API_URL=$VITE_NODE_API_URL
ENV VITE_PY_API_URL=$VITE_PY_API_URL
WORKDIR /app
COPY package*.json ./
RUN if [ "$MIRROR" = "china" ]; then \
      npm ci --registry=https://registry.npmmirror.com; \
    else \
      npm ci; \
    fi
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
