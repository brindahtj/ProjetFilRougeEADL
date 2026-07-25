import pika


import logging


from Api_ingestion.publisher import RabbitMQPublisher


def test_rabbitmq_connection_error_is_handled(mocker, caplog):
    mock_connection = mocker.patch(
        "Api_ingestion.publisher.pika.BlockingConnection",
        side_effect=pika.exceptions.AMQPConnectionError(
            "RabbitMQ indisponible"
        ),
    )

    publisher = RabbitMQPublisher(
        host="localhost",
        port=5672,
        user="guest",
        password="guest",
        vhost="/",
    )

    with caplog.at_level(logging.ERROR):
        result = publisher.notify(
            {"message": "alerte critique"},
            routing_key="critical_alerts",
        )

    assert result is False
    mock_connection.assert_called_once()
    assert "Échec de publication RabbitMQ" in caplog.text