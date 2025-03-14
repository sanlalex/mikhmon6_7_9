FROM php:7.4-apache

# Installer les extensions PHP nécessaires
RUN docker-php-ext-install mysqli pdo pdo_mysql

# Créer des répertoires pour les données persistantes
RUN mkdir -p /var/www/html/data

# Copier les fichiers de l'application
COPY . /var/www/html/

# Configurer Apache
RUN a2enmod rewrite
RUN mkdir -p /etc/apache2/sites-available
COPY apache-config.conf /etc/apache2/sites-available/000-default.conf

# Définir les permissions
RUN chown -R www-data:www-data /var/www/html
RUN chmod -R 755 /var/www/html

# Définir les volumes pour les données persistantes
VOLUME ["/var/www/html/include", "/var/www/html/hotspot", "/var/www/html/voucher", "/var/www/html/settings", "/var/www/html/datat"]

EXPOSE 80

CMD ["apache2-foreground"]