import pyinotify
import json
import time
import logging
import logging.config

from app.configuration import configure_enhancer_services
from app.utils.container import container
from app.models.Carpool import Carpool
from app.utils.utils import agency_carpool_ids_from_filename

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger("enhancer")

logger.info("Hello Enhancer")

configure_enhancer_services()

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CLOSE_WRITE


class EventHandler(pyinotify.ProcessEvent):
    # TODO FG HB should watch for both carpools and agencies
    # in data/agency, data/agencyconf, see AgencyConfService

    def process_IN_CLOSE_WRITE(self, event):
  
        logger.info("CLOSE_WRITE: Created %s", event.pathname)
        try:
            with open(event.pathname, 'r', encoding='utf-8') as f:
                dict = json.load(f)
                carpool = Carpool(**dict)

            container['carpools'].put(carpool.agency, carpool.id, carpool)
        except FileNotFoundError as e:
            logger.error("Carpool could not be added, as already deleted (%s)", event.pathname)
        except:
            logger.exception("Eventhandler process_IN_CLOSE_WRITE encountered exception")        

    def process_IN_DELETE(self, event):
        try:
            logger.info("DELETE: Removing %s", event.pathname)
            (agency_id, carpool_id) = agency_carpool_ids_from_filename(event.pathname)
            container['carpools'].delete(agency_id, carpool_id)
        except:
            logger.exception("Eventhandler process_IN_DELETE encountered exception")
        

notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
notifier.start()

wdd = wm.add_watch('data/carpool', mask, rec=True)
import time

try:
    # TODO FG Is this really needed?
    cnt = 0
    ENHANCER_LOG_INTERVAL_IN_S = 600
    while True:
        if cnt == ENHANCER_LOG_INTERVAL_IN_S:
            logger.debug("Currently stored carpool ids: %s", container['carpools'].get_all_ids())
            cnt = 0

        time.sleep(1)
        cnt += 1
finally:
    wm.rm_watch(list(wdd.values()))

    notifier.stop()

    logger.info("Goodbye Enhancer")
