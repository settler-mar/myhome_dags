#set PWD in HOME variable
HOME=$(pwd)

cd /etc/systemd/system
sudo systemctl stop serial-getty@ttyAML0.service
sudo systemctl mask serial-getty@ttyAML0.service
sudo awk '{gsub(/console=ttyAML0,115200n8/,"")}1' /boot/uEnv.txt > /tmp/uEnv.txt
sudo rm /boot/uEnv.txt
sudo mv /tmp/uEnv.txt /boot/uEnv.txt


cd /tmp
sudo apt-get update
sudo apt install curl -y
curl -fsSL https://deb.nodesource.com/setup_21.x | sudo -E bash -
sudo apt install nodejs -y
sudo npm install --global yarn
sudo npm install -g sass
sudo apt install python3-pip -y
curl -fsSL https://get.docker.com -o get-docker.sh
chmod +x get-docker.sh
sudo ./get-docker.sh

cd /tmp
sudo apt-get install ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt-get install docker-compose -y

sudo apt install openjdk-11-jre -y

cd /tmp
wget http://archive.apache.org/dist/activemq/5.16.3/apache-activemq-5.16.3-bin.tar.gz
sudo tar -xvzf apache-activemq-5.16.3-bin.tar.gz
sudo mkdir /opt/activemq
sudo mv apache-activemq-5.16.3/* /opt/activemq
sudo addgroup --quiet --system activemq
sudo adduser --quiet --system --ingroup activemq --no-create-home --disabled-password activemq
sudo chown -R activemq:activemq /opt/activemq

#create /etc/systemd/system/activemq.service
sudo cat <<EOF > /tmp/activemq.service
[Unit]
 Description=Apache ActiveMQ
 After=network.target
 [Service]
 Type=forking
 User=activemq
 Group=activemq

 ExecStart=/opt/activemq/bin/activemq start
 ExecStop=/opt/activemq/bin/activemq stop

 [Install]
 WantedBy=multi-user.target
EOF
sudo mv /tmp/activemq.service /etc/systemd/system/activemq.service
sudo update-rc.d activemq defaults
# replace 127.0.0.1 to 0.0.0.0 in /opt/activemq/conf/jetty.xml
sudo awk '{gsub(/127.0.0.1/,"0.0.0.0")}1' /opt/activemq/conf/jetty.xml > /tmp/jetty.xml
sudo mv /tmp/jetty.xml /opt/activemq/conf/jetty.xml
sudo systemctl daemon-reload
sudo systemctl start activemq
sudo systemctl enable activemq

# run run.sh from current directory as service
#sudo cat <<EOF > /tmp/server_app.service
#[Unit]
#Description=server_app
#
#[Service]
#ExecStart=/bin/bash $HOME/run.sh
#
#[Install]
#WantedBy=multi-user.target
#EOF
#sudo mv /tmp/server_app.service /etc/systemd/system/server_app.service
#sudo systemctl daemon-reload
#sudo systemctl start server_app

sudo cat <<EOF > /tmp/my_server
#!/bin/bash

### BEGIN INIT INFO
# Provides:          My_server
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Example initscript
# Description:       This service is used to manage a servo
### END INIT INFO

case "$1" in
    start)
        echo "Starting my server"
        cd $HOME
        make run
        ;;
    stop)
        echo "Stopping my server"
        ;;
    *)
        echo "Usage: /etc/init.d/my_server start"
        exit 1
        ;;
esac

exit 0
EOF
#sudo mv /tmp/my_server /etc/init.d/my_server
#sudo chmod 755 /etc/init.d/my_server
#sudo chown root:root /etc/init.d/my_server
#sudo update-rc.d my_server defaults

#go to backend directory
cd $HOME/backend
python3 -m pip install uvicorn --break-system-packages
python3 -m pip install pyyaml --break-system-packages
pip3 install -r requirements.txt --break-system-packages

#go to frontend directory
cd $HOME/frontend
yarn install
yarn run build