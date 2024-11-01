import os
import subprocess
from time import sleep
import secrets
import re
import sys


# Configuration
USER = "sanlalex"
REPO = "mikhmon6_7_9"
BRANCH = "dev" #dev
GITHUB_TOKEN = "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"  

def main():
    print("\033[92m" + "Bienvenue sur le script de deployment..." + "\033[0m")
    print("\033[92m" + "Entrez le nom de domaine nom.domaine.tld  et le port..." + "\033[0m")
    domain_name = input("Entrer le nom de domaine: ")

    # Enlever tous les points du nom de domaine
    domain = domain_name.replace('.', '')
    directory_folder = "/home/mikhmononline/"+ domain
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
    create_docker_compose(working_directory)

    # Build et lancement des conteneurs Docker
    print("\033[92m" + "Construction et lancement des conteneurs Docker..." + "\033[0m")
    try:
        subprocess.run(["docker-compose", "up", "-d", "--build"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du lancement des conteneurs Docker : {e}")
        return

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

EXPOSE 802

CMD ["apache2-foreground"]

"""

    with open(f"{working_directory}/Dockerfile", "w") as f:
        f.write(dockerfile_content)


def create_docker_compose(working_directory):
    docker_compose_content = f"""
version: '3.8'

services:
  web:
    image: php:7.4-apache
    container_name: php_apache_server
    ports:
      - "80:80"
    volumes:
      - /home/data:/var/www/html
      - ./apache-config.conf:/etc/apache2/sites-available/000-default.conf
    environment:
      APACHE_RUN_USER: www-data
      APACHE_RUN_GROUP: www-data
    command: ["apache2-foreground"]
    working_dir: /var/www/html
    restart: always

    # Utiliser le Dockerfile pour l'installation des extensions et la configuration d'Apache
    build:
      context: .
      dockerfile: Dockerfile
"""
    with open(f"{working_directory}/docker-compose.yaml", "w") as f:
        f.write(docker_compose_content)


if __name__ == "__main__":
    main()