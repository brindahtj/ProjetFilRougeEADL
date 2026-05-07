# Démarrer RabbitMQ
rabbitmq-server

# Arrêter RabbitMQ
rabbitmqctl stop
# Ajouter un utilisateur
rabbitmqctl add_user nom_utilisateur mot_de_passe

# Définir les permissions
rabbitmqctl set_permissions -p / nom_utilisateur ".*" ".*" ".*"

# Lister les utilisateurs
rabbitmqctl list_users

# Supprimer un utilisateur
rabbitmqctl delete_user nom_utilisateur
# Lister les exchanges
rabbitmqctl list_exchanges

# Lister les queues
rabbitmqctl list_queues

# Lister les bindings
rabbitmqctl list_bindings

# Purger une queue (vider les messages)
rabbitmqctl purge_queue nom_queue

# Ouvrir la console d'administration
Start-Process "http://localhost:15672"

##Identifiants par défaut
## Utilisateur : guest
## Mot de passe : guest

# Vérifier le statut
rabbitmqctl status

# Diagnostic complet
rabbitmqctl diagnostics

# Réinitialiser RabbitMQ
rabbitmqctl reset

Pour activer RabbitMQ et vérifier qu'il fonctionne sur localhost après set-location :
# 1. Aller au répertoire RabbitMQ
Set-Location 'C:\Program Files\RabbitMQ Server\rabbitmq_server-4.3.0\sbin'

# 2. Vérifier l'état du service RabbitMQ
Get-Service RabbitMQ

# 3. Démarrer le service s'il n'est pas actif
Start-Service RabbitMQ

# 4. Attendre quelques secondes et vérifier que c'est bien lancé
Get-Service RabbitMQ | Select-Object Status

# 5. Activer le plugin management (interface web sur port 15672)
.\rabbitmq-plugins.bat enable rabbitmq_management

# 6. Attendre 5-10 secondes que le plugin se charge
Start-Sleep -Seconds 10

# 7. Vérifier les ports écoutés
netstat -anob | Select-String "15672"
netstat -anob | Select-String "5672"

# 8. Tester la connexion RabbitMQ (AMQP port 5672)
Test-NetConnection -ComputerName localhost -Port 5672

# 9. Tester l'interface management (HTTP port 15672)
Test-NetConnection -ComputerName localhost -Port 15672

# 10. Ouvrir l'interface web dans le navigateur
Start-Process "http://localhost:15672"
# Identifiants par défaut : guest / guest