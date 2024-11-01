import os
import subprocess
from time import sleep
import secrets
import re
import sys
from database_creation import create_database
from redis_script import create_redis
from nginx_port_manager import get_available_port

# Configuration
USER = "sanlalex"
REPO = "Sunpaysaas"
BRANCH = "multi_integrateur" #dev
DJANGO_APP = "Sunpaysaas"
GITHUB_TOKEN = "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"  # Remplacez par votre token

def main():
    print("\033[92m" + "Bienvenue sur le script de deployment Docker..." + "\033[0m")
    print("\033[92m" + "Entrez le nom de domaine nom.domaine.tld et le port..." + "\033[0m")
    domain_name = input("Entrer le nom de domaine: ")

    # Enlever tous les points du nom de domaine
    domain = domain_name.replace('.', '')
    port = get_available_port()
    directory_folder = "/home/" + domain
    working_directory = f"{directory_folder}/{REPO}"

    # Créer le répertoire si nécessaire
    if not os.path.exists(directory_folder):
        os.makedirs(directory_folder)

    # Clone the repository
    print("\033[92m" + "Clonage du repository ..." + "\033[0m")
    os.chdir(directory_folder)
    try:
        subprocess.run(["rm", '-rf', working_directory])
        repo_url = f"https://{USER}:{GITHUB_TOKEN}@github.com/{USER}/{REPO}.git"
        subprocess.run(["git", "clone", "-b", BRANCH, repo_url], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du clonage du repository : {e}")
        return

    # Change to project directory
    os.chdir(f"./{REPO}")

    # CREATION DE LA BASE DE DONNEE
    create_database(domain)

    # CREATION DE REDIS
    external_db_url = create_redis(domain)

    print('external_db_url', external_db_url)

    # Modification de settings
    SECRET_KEY = secrets.token_urlsafe(50)
    settings_path = os.path.join(working_directory, 'sunpay', 'settings.py')
    with open(settings_path, 'r') as file:
        settings = file.read()

    # Mise à jour des paramètres de base de données
    settings = settings.replace("'ENGINE': 'django.db.backends.sqlite3'", "'ENGINE': 'django.db.backends.postgresql'")
    settings = settings.replace("'NAME': BASE_DIR / 'db.sqlite3'", f"'NAME': '{domain}',\n        'USER': 'postgres',\n        'PASSWORD': 'Sanlalex1993',\n        'HOST': '158.178.207.178',\n        'PORT': '5432'")
    
    # Remplacement de la clé secrète
    settings = re.sub(r"SECRET_KEY\s*=\s*['\"].*['\"]", f"SECRET_KEY = '{SECRET_KEY}'", settings)
    
    # Mettre Debug à False
    settings = settings.replace('DEBUG = True', 'DEBUG = False')
    settings = re.sub(r"CELERY_BROKER_URL\s*=\s*['\"].*['\"]", f"CELERY_BROKER_URL = '{external_db_url}'", settings)

    with open(settings_path, 'w') as file:
        file.write(settings)

    # Création du Dockerfile
    create_dockerfile(working_directory)

    # Création du docker-compose.yml
    create_docker_compose(domain, port, working_directory, external_db_url)

    # Build et lancement des conteneurs Docker
    print("\033[92m" + "Construction et lancement des conteneurs Docker..." + "\033[0m")
    try:
        subprocess.run(["docker-compose", "up", "-d", "--build"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du lancement des conteneurs Docker : {e}")
        return

    # Configure Nginx
    configure_nginx(domain_name, working_directory, port)

    # Install SSL certificates
    install_ssl(domain_name)

    print("Déploiement Docker terminé avec succès!")

def create_dockerfile(working_directory):
    dockerfile_content = """
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -i https://test.pypi.org/simple/ cinetpay-sdk==0.1.1
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "sunpay.wsgi:application"]
"""
    with open(f"{working_directory}/Dockerfile", "w") as f:
        f.write(dockerfile_content)

def create_docker_compose(domain, port, working_directory, external_db_url):
    docker_compose_content = f"""
version: '3'

services:
  web:
    build: .
    container_name: {domain}_web
    image: {domain}_image
    restart: always
    ports:
      - "{port}:8000"
"""
    with open(f"{working_directory}/docker-compose.yml", "w") as f:
        f.write(docker_compose_content)



def configure_nginx(domain_name, working_directory, port):
    NGINX_CONF_TEMPLATE = """
    server {{
        server_name {domain_name} www.{domain_name};

        location /static {{
            alias {working_directory}/static;
        }}

        location / {{
            proxy_set_header Host $http_host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_redirect off;
            proxy_pass http://127.0.0.1:{port};
        }}
        gzip_types text/css text/less text/plain text/xml application/xml application/json application/javascript;   
        gzip on;
    }}
    """

    print("\033[92m" + "Configuration de Nginx..." + "\033[0m")
    
    nginx_conf_file = os.path.join("/etc/nginx/sites-available", domain_name)
    if os.path.exists(nginx_conf_file):
        os.remove(nginx_conf_file)

    link_file = os.path.join("/etc/nginx/sites-enabled", domain_name)
    if os.path.exists(link_file):
        os.remove(link_file)

    nginx_conf = NGINX_CONF_TEMPLATE.format(domain_name=domain_name, working_directory=working_directory, port=port)
    with open(f"/etc/nginx/sites-available/{domain_name}", "w") as f:
        f.write(nginx_conf)

    # Create symbolic link
    print("\033[92m" + "Création lien symbolique..." + "\033[0m")
    try:
        subprocess.run(["sudo", "ln", "-sf", f"/etc/nginx/sites-available/{domain_name}", f"/etc/nginx/sites-enabled/{domain_name}"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la création du lien symbolique : {e}")
        return

    # Restart Nginx
    print("\033[92m" + "Redémarrage de Nginx..." + "\033[0m")
    try:
        subprocess.run(["sudo", "systemctl", "restart", "nginx"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du redémarrage de Nginx : {e}")
        return

def install_ssl(domain_name):
    print("\033[92m" + "Installation SSL ..." + "\033[0m")
    try:
        subprocess.run(["sudo", "certbot", "--nginx", "-d", domain_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'installation des certificats SSL : {e}")

if __name__ == "__main__":
    main()