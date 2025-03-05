origin https://hub.docker.com/r/rmohr/activemq
https://github.com/terdia/mqttui

## Settings

You can define the following environment variables to control the behavior. 

| Environment Variable                    | Default | Description                                                                                                                                                                   |
|:----------------------------------------|:--------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ACTIVEMQ_USERNAME                       | system  | [Security](https://activemq.apache.org/security) (credentials.properties)                                                                                                     |
| ACTIVEMQ_PASSWORD                       | manager | [Security](https://activemq.apache.org/security) (credentials.properties)                                                                                                     |
| ACTIVEMQ_WEBADMIN_USERNAME              | admin   | [WebConsole](https://activemq.apache.org/security) (jetty-realm.properties)                                                                                                   |
| ACTIVEMQ_WEBADMIN_PASSWORD              | admin   | [WebConsole](https://activemq.apache.org/security) (jetty-realm.properties)                                                                                                   |
| ACTIVEMQ_WEBCONSOLE_USE_DEFAULT_ADDRESS | false   | Set default behavior of ActiveMQ Jetty listen address (127.0.0.1). By default, WebConsole listens on all addresses (0.0.0.0), so you can reach/map the WebConsole port (8161) |
| ACTIVEMQ_ADMIN_CONTEXTPATH              | /admin  | [WebConsole](https://github.com/apache/activemq/blob/main/assembly/src/release/conf/jetty.xml) Set contextPath of WebConsole (jetty.xml)                                      |
| ACTIVEMQ_API_CONTEXTPATH                | /api    | [API](https://github.com/apache/activemq/blob/main/assembly/src/release/conf/jetty.xml) Set contextPath of API (jetty.xml)                                                    |
| ACTIVEMQ_ENABLE_SCHEDULER               | false   | Enable the scheduler by setting `schedulerSupport` to `true` in `activemq.xml`|


## Exposed Ports

The following ports are exposed and can be bound:

| Port  | Description |
|:------|:------------|
| 1883  | MQTT        |
| 5672  | AMPQ        |
| 8161  | WebConsole  |
| 61613 | STOMP       |
| 61614 | WS          |
| 61616 | OpenWire    |