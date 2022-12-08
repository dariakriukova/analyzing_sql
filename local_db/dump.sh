docker run --rm -it mysql:latest mysqldump --no-tablespaces --host=95.217.222.91 --user=exporter --port=3306 -p elfys --where="1 limit 1" | gzip -9 > dump.sql.tar.gz
