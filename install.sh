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
npm install --global yarn
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
