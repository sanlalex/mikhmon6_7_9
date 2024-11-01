import os
import subprocess
from time import sleep
import secrets
import re
import sys


# Configuration
USER = "sanlalex"
REPO = "mikhmon7_10_7_15"
BRANCH = "main" #dev
GITHUB_TOKEN = "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"  

def main():
    print("\033[92m" + "Bienvenue sur le script de deployment..." + "\033[0m")
    print("\033[92m" + "Entrez le nom de domaine nom.domaine.tld  et le port..." + "\033[0m")
    domain_name = input("Entrer le nom de domaine: ")

    # Enlever tous les points du nom de domaine
    domain = domain_name.replace('.', '')
    directory_folder = "/home/mikhmononline"+ domain
    # Créer le répertoire si nécessaire
    if not os.path.exists(directory_folder):
        os.makedirs(directory_folder)
    working_directory = f"{directory_folder}/" + REPO


    # Clone the repository
    print("\033[92m" + "Clonnage du repository ..." + "\033[0m")
    os.chdir(f"{directory_folder}")  
    try:
        subprocess.run(["rm", '-rf', working_directory ])
        repo_url = f"https://{USER}:{GITHUB_TOKEN}@github.com/{USER}/{REPO}.git"
        subprocess.run(["git", "clone", "-b", BRANCH, repo_url], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du clonage du repository : {e}")
        return

    # Change to project directory
    os.chdir(f"./{REPO}")

    # Création du Dockerfile
    create_dockerfile(working_directory)

    # Création du docker-compose.yml
    #create_docker_compose(domain, port, working_directory, external_db_url)

    # Build et lancement des conteneurs Docker
    print("\033[92m" + "Construction et lancement des conteneurs Docker..." + "\033[0m")
    try:
        subprocess.run(["docker-compose", "up", "-d", "--build"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du lancement des conteneurs Docker : {e}")
        return

    # Configure Nginx
    #configure_nginx(domain_name, working_directory, port)

    # Install SSL certificates
    #install_ssl(domain_name)

    print("Déploiement Docker terminé avec succès!")

def create_dockerfile(working_directory):
    dockerfile_content = """
FROM php:7.4-apache

# Installer les extensions PHP nécessaires
RUN docker-php-ext-install mysqli pdo pdo_mysql

# Copier les fichiers de l'application
COPY . /var/www/html/

# Configurer Apache
RUN a2enmod rewrite
COPY apache-config.conf /etc/apache2/sites-available/000-default.conf

# Définir les permissions
RUN chown -R www-data:www-data /var/www/html
RUN chmod -R 755 /var/www/html

EXPOSE 80

CMD ["apache2-foreground"]
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