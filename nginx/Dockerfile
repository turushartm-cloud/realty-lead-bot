FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY ../mini-app /usr/share/nginx/html/mini-app
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
