FROM nginx:1.27-alpine
COPY . /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Compose image is same-origin /api via this NGINX. Never bake dual-process
# config.local.js (host :8000) from a lab tree that ran START_FRONTEND.bat.
RUN printf '%s\n' '// same-origin Compose defaults' > /usr/share/nginx/html/js/config.local.js
EXPOSE 80
