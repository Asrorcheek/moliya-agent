#!/usr/bin/env python3
"""Run durable browser regressions against a disposable local app."""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.ui import WebDriverWait

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_server(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"Server stopped early\n{stdout}\n{stderr}")
        try:
            with urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except URLError:
            time.sleep(0.1)
    raise RuntimeError("Server did not become healthy within 20 seconds")


def run_browser(base_url: str) -> list[str]:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,1000")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    passed: list[str] = []

    def present(selector: str):
        return wait.until(expected.presence_of_element_located((By.CSS_SELECTOR, selector)))

    def gone(selector: str) -> None:
        wait.until(expected.invisibility_of_element_located((By.CSS_SELECTOR, selector)))

    def escape() -> None:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    def path_ends_with(path: str) -> None:
        wait.until(lambda browser: browser.current_url.split("?", 1)[0].endswith(path))

    try:
        driver.get(base_url)
        fields = wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, "form input"))
        fields[0].send_keys("admin")
        fields[1].send_keys("dev-admin")
        driver.find_element(By.CSS_SELECTOR, "form button[type=submit]").click()
        present(".floating-add-button")

        driver.find_element(By.CSS_SELECTOR, ".floating-add-button").click()
        path_ends_with("/add")
        present(".add-page-toolbar .icon-button").click()
        path_ends_with("/")
        passed.append("add closes with X and returns to origin")

        driver.find_element(By.CSS_SELECTOR, ".floating-add-button").click()
        path_ends_with("/add")
        escape()
        path_ends_with("/")
        passed.append("add closes with Escape")

        driver.get(f"{base_url}/users")
        for mode in ("x", "escape", "backdrop"):
            present(".toolbar-add-user").click()
            present(".admin-drawer")
            if mode == "x":
                driver.find_element(By.CSS_SELECTOR, ".admin-drawer-heading .icon-button").click()
            elif mode == "escape":
                escape()
            else:
                overlay = driver.find_element(By.CSS_SELECTOR, ".admin-drawer-overlay")
                driver.execute_script("arguments[0].click()", overlay)
            gone(".admin-drawer")
        passed.append("user drawer closes with X, Escape, and backdrop")

        driver.get(f"{base_url}/settings")
        present(".google-integration-card")
        connect_button = present(".google-connect-panel button")
        assert not connect_button.is_enabled()
        passed.append("Google integration shows safe unconfigured state")

        driver.get(f"{base_url}/add")
        present(".example-chip").click()
        driver.find_element(By.CSS_SELECTOR, "form button[type=submit]").click()
        wait.until(
            lambda browser: len(browser.find_elements(By.CSS_SELECTOR, ".add-step-heading")) >= 2
        )
        driver.get(f"{base_url}/drafts")
        for mode in ("x", "escape", "backdrop"):
            present("main button").click()
            dialog = present('[role="dialog"]')
            if mode == "x":
                dialog.find_element(By.CSS_SELECTOR, ".dialog-heading .icon-button").click()
            elif mode == "escape":
                escape()
            else:
                driver.execute_script("arguments[0].click()", dialog)
            gone('[role="dialog"]')
        passed.append("confirmation dialog closes with X, Escape, and backdrop")

        present("main button").click()
        dialog = present('[role="dialog"]')
        dialog.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]').click()
        dialog.find_elements(By.CSS_SELECTOR, "button")[-1].click()
        gone('[role="dialog"]')

        driver.get(f"{base_url}/transactions")
        for mode in ("x", "escape", "backdrop"):
            present(".desktop-table tbody tr").click()
            detail = present('[role="dialog"]')
            if mode == "x":
                detail.find_element(By.CSS_SELECTOR, ".icon-button").click()
            elif mode == "escape":
                escape()
            else:
                driver.execute_script("arguments[0].click()", detail)
            gone('[role="dialog"]')
        passed.append("transaction drawer closes with X, Escape, and backdrop")

        driver.delete_cookie("moliya_session")
        driver.find_element(By.CSS_SELECTOR, 'a[href="/drafts"]').click()
        present('input[autocomplete="current-password"]')
        assert not driver.find_elements(By.XPATH, "//*[contains(text(), 'Xatolik yuz berdi')]")
        passed.append("expired session redirects to login without generic error")

        severe = [
            entry
            for entry in driver.get_log("browser")
            if entry["level"] == "SEVERE"
            and not ("401" in entry["message"] and "/v1/session" in entry["message"])
            and not ("401" in entry["message"] and "/v1/drafts" in entry["message"])
        ]
        assert not severe, f"Unexpected browser console errors: {severe}"
        return passed
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    if not args.skip_build:
        subprocess.run(["npm", "run", "build"], cwd=APP_DIR, check=True)

    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="moliya-browser-regression-") as directory:
        environment = os.environ.copy()
        environment.update(
            {
                "PYTHONPATH": str(PROJECT_ROOT / "src"),
                "MOLIYA_DB_PATH": str(Path(directory) / "test.db"),
                "MOLIYA_WEB_DIST_DIR": str(APP_DIR / "dist"),
                "MOLIYA_WEB_USERNAME": "admin",
                "MOLIYA_WEB_PASSWORD": "dev-admin",
            }
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "moliya_agent.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            wait_for_server(base_url, process)
            checks = run_browser(base_url)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    print("browser_regressions=ok")
    for check in checks:
        print(f"  - {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
