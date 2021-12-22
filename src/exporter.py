"""Application exporter"""

import os
import time
import datetime
from balena import Balena
from prometheus_client import start_http_server, Gauge, Enum

balena = Balena()


class AppMetrics:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, polling_interval_seconds=5):
        self.polling_interval_seconds = polling_interval_seconds

        # Prometheus metrics to collect
        self.applicationCount = Gauge("balena_count_applications", "All active Applications")
        self.deviceCount = Gauge("balena_count_devices", "All existing devices")
        self.deviceMemory = Gauge("balena_device_memory_usage", "Device Memory Usage",
                                  ['deviceuuid', 'application', 'release'])
        self.deviceStatus = Enum("balena_device_status", "Device Status", ['deviceuuid', 'application', 'release'],states=['Idle','Running','Updating','None'])
        self.deviceOverallStatus = Enum("balena_device_overall_status"," Device Overall State", ['deviceuuid', 'application', 'release'],states=['online','offline','configuring','None','updating'])
        self.devicesOnRelease = Gauge("balena_release_number_devices","Number of Devices Running specific Release", ['release'])
        self.releaseCreatedAt = Gauge("balena_release_created_at", "Time where Release was created", ['release'])
    def run_metrics_loop(self):
        """Metrics fetching loop"""

        while True:
            self.fetch()
            time.sleep(self.polling_interval_seconds)

    def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """

        # Fetch raw status data from the application
        applications = balena.models.application.get_all()
        self.applicationCount.set(len(applications))

        devices = balena.models.device.get_all()
        self.deviceCount.set(len(devices))

        for device in devices:
            appSlug = [application['app_name'] for application in applications if application['id'] == device['belongs_to__application']['__id']]
            if device['is_running__release']:
                release = balena.models.release.get(device['is_running__release']['__id'])
            self.deviceMemory.labels(deviceuuid=device['uuid'], application=appSlug, release=release['commit'] or "None").set(
                device['memory_usage'] or "0")
            self.deviceStatus.labels(deviceuuid=device['uuid'], application=appSlug, release=release['commit'] or "None").state(
                device['status'] or 'None')
            self.deviceOverallStatus.labels(deviceuuid=device['uuid'], application=appSlug, release=release['commit'] or "None").state(
                device['overall_status'] or 'None')
            self.devicesOnRelease.labels(release=release['commit'] or "None").inc()
            self.releaseCreatedAt.labels(release=release['commit'] or "None").set(datetime.datetime.strptime(release['created_at'],"%Y-%m-%dT%H:%M:%S.%fZ").timestamp())
        # Update Prometheus metrics with application metrics


def main():
    """Main entry point"""

    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "60"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))

    balenaUrl = os.getenv("BALENA_API_URI", "https://api.balena-cloud.de")
    balenaUser = os.getenv("BALENA_USER", "admin")
    balenaPwd = os.getenv("BALENA_PWD", "********")

    credentials = {'username': balenaUser, 'password': balenaPwd}
    balena.settings.set(key='pine_endpoint', value=balenaUrl+'/v6/')
    balena.settings.set(key='api_endpoint', value=balenaUrl+'/')
    balena.auth.login(**credentials)
    app_metrics = AppMetrics(
        polling_interval_seconds=polling_interval_seconds
    )
    start_http_server(exporter_port)
    app_metrics.run_metrics_loop()


if __name__ == "__main__":
    main()
