FROM nginx:1.27-alpine

COPY apps/eyt-catalog/nginx.conf /etc/nginx/conf.d/default.conf
COPY apps/eyt-catalog/ /usr/share/nginx/html/

EXPOSE 80
