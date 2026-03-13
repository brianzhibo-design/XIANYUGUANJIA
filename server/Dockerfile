FROM node:20-alpine

ARG MIRROR=international
# 国内构建: docker build --build-arg MIRROR=china .

WORKDIR /app
RUN addgroup -S appgrp && adduser -S appusr -G appgrp
COPY package*.json ./
RUN if [ "$MIRROR" = "china" ]; then \
      npm ci --omit=dev --registry=https://registry.npmmirror.com; \
    else \
      npm ci --omit=dev; \
    fi
COPY src/ ./src/
RUN mkdir -p /app/data && chown -R appusr:appgrp /app
USER appusr
EXPOSE 3001
CMD ["node", "src/app.js"]
