FROM nginx:1.27-alpine
COPY . /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Optional local override file may be absent in image builds; keep script tag safe.
RUN if [ ! -f /usr/share/nginx/html/js/config.local.js ]; then echo "// same-origin defaults" > /usr/share/nginx/html/js/config.local.js; fi
EXPOSE 80
