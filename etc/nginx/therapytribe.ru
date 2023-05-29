harset utf-8;
client_max_body_size 30M;
index index.html index.htm;
set_real_ip_from 172.17.0.0/16;
real_ip_header X-Forwarded-For;
real_ip_recursive on;

rewrite ^/favicon.ico$ http://therapytribe.ru/static/images/favicon/favicon.ico;
rewrite ^/favicon.png$ http://therapytribe.ru/static/images/favicon/favicon-32x32.png;

location /static/ {
  root /root/adm/therapytribe/frontend/;
  gzip_static on;
  expires max;
  add_header Cache-Control "public";
}

location /downloads/ {
  root /root/adm/therapytribe/gdpr/;
  gzip_static off;
  expires max;
  add_header Cache-Control "public";
}
