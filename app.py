import json
import connexion
import datetime
import logging
import logging.config
import requests
import yaml
from connexion import NoContent
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread

from flask_cors import CORS, cross_origin
from pykafka import KafkaClient

with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')


def populate_stats():
    """ Periodically updating stats """
    logger.info("Start Periodic Processing")

    statistics = {
        "num_inventory_readings": 0,
        "num_status_readings": 0,
        "updated_timestamp": "2016-01-01 00:00:01.001000"
    }

    with open(app_config['datastore']['filename'], 'r') as f:
        statistics = json.loads(f.read())

    start_date = statistics["updated_timestamp"]
    end_date = datetime.datetime.now()

    params = {
        "start_date": start_date,
        "end_date": end_date
    }

    r1 = requests.get(app_config['eventstore']['url'], params=params)

    if r1.status_code != 200:
        logger.error("Service error while getting updated stats for inventory reports")
    else:
        logger.info("Number of inventory report events received: {}".format(len(r1.json())))

    r2 = requests.get(app_config['eventstore']['url2'], params=params)

    if r2.status_code != 200:
        logger.error("Service error while getting updated stats for inventory reports")
    else:
        logger.info("Number of inventory report events received: {}".format(len(r2.json())))

    new_statistics = {
        "num_inventory_readings": len(r1.json()) + statistics["num_inventory_readings"],
        "num_status_readings": len(r2.json()) + statistics["num_status_readings"],
        "updated_timestamp": end_date.strftime("%Y-%m-%d %H:%M:%S.%f")
    }

    with open(app_config['datastore']['filename'], 'w') as f:
        json.dump(new_statistics, f)

    logger.debug("new stats: {}".format(new_statistics))

    logger.info("Ending Periodic Processing")


def init_scheduler():
    """ Scheduler """
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats,
                  'interval',
                  seconds=app_config['scheduler']['period_sec'])
    sched.start()


def get_report_stats():
    logger.info("Start Periodic Processing")

    statistics = None

    with open(app_config['datastore']['filename'], 'r') as f:
        statistics = json.loads(f.read())

    if statistics is None:
        logger.error("Could not find file")
        return 404

    logger.debug("new stats: {}".format(statistics))
    logger.info("Ending Periodic Processing")

    return statistics, 200


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml")

CORS(app.app)
app.app.config['CORS_HEADERS'] = 'Content-Type'

if __name__ == "__main__":
    # run our standalone get event server
    init_scheduler()
    app.run(port=8100, use_reloader=False)
