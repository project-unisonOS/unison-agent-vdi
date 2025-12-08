from __future__ import annotations

import asyncio
import uuid
import os
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .models import BrowseAction, BrowseRequest, DownloadRequest, FormField, FormSubmitRequest, TaskResult

DEFAULT_TIMEOUT = int(1000 * float(int(os.environ.get("VDI_ACTION_TIMEOUT_SECONDS", "15"))))


class BrowserRunner:
    async def browse(self, request: BrowseRequest, workspace: Path) -> TaskResult:
        raise NotImplementedError

    async def submit_form(self, request: FormSubmitRequest, workspace: Path) -> TaskResult:
        raise NotImplementedError

    async def download(self, request: DownloadRequest, workspace: Path) -> TaskResult:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class FakeBrowserRunner(BrowserRunner):
    """Lightweight stub used in tests or constrained environments."""

    async def browse(self, request: BrowseRequest, workspace: Path) -> TaskResult:
        workspace.mkdir(parents=True, exist_ok=True)
        return TaskResult(status="ok", detail="fake-browser", telemetry={"url": str(request.url)})

    async def submit_form(self, request: FormSubmitRequest, workspace: Path) -> TaskResult:
        workspace.mkdir(parents=True, exist_ok=True)
        return TaskResult(status="ok", detail="fake-form-submit", telemetry={"fields": str(len(request.form))})

    async def download(self, request: DownloadRequest, workspace: Path) -> TaskResult:
        workspace.mkdir(parents=True, exist_ok=True)
        dummy = workspace / (request.filename or "placeholder.txt")
        dummy.write_text("placeholder")
        return TaskResult(
            status="ok",
            detail="fake-download",
            artifacts=[str(dummy)],
            telemetry={"url": str(request.url)},
        )

    async def close(self) -> None:
        return None


class PlaywrightBrowserRunner(BrowserRunner):
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        async with self._lock:
            if self._browser is None:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-setuid-sandbox",
                    ],
                )
            return self._browser

    async def _context(self, request: BrowseRequest, workspace: Path) -> BrowserContext:
        browser = await self._ensure_browser()
        workspace.mkdir(parents=True, exist_ok=True)
        context = await browser.new_context(accept_downloads=True, base_url=None, extra_http_headers=request.headers)
        context.set_default_timeout(DEFAULT_TIMEOUT)
        await context.tracing.start(screenshots=False, snapshots=False)
        await context.set_default_navigation_timeout(DEFAULT_TIMEOUT)
        return context

    async def _apply_actions(self, page: Page, actions: List[BrowseAction]) -> None:
        for action in actions:
            if action.click_selector:
                await page.click(action.click_selector)
            if action.wait_for:
                await page.wait_for_selector(action.wait_for)

    async def browse(self, request: BrowseRequest, workspace: Path) -> TaskResult:
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None
        try:
            context = await self._context(request, workspace)
            page = await context.new_page()
            await page.goto(str(request.url))
            if request.wait_for:
                await page.wait_for_selector(request.wait_for)
            await self._apply_actions(page, request.actions)
            return TaskResult(status="ok", telemetry={"url": str(request.url)})
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def submit_form(self, request: FormSubmitRequest, workspace: Path) -> TaskResult:
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None
        try:
            context = await self._context(request, workspace)
            page = await context.new_page()
            await page.goto(str(request.url))
            for field in request.form:
                if field.type == "checkbox":
                    await page.check(field.selector)
                else:
                    await page.fill(field.selector, field.value)
            if request.submit_selector:
                await page.click(request.submit_selector)
            if request.wait_for:
                await page.wait_for_selector(request.wait_for)
            await self._apply_actions(page, request.actions)
            return TaskResult(status="ok", telemetry={"url": str(request.url), "fields": str(len(request.form))})
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def download(self, request: DownloadRequest, workspace: Path) -> TaskResult:
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None
        downloads: List[str] = []
        try:
            context = await self._context(request, workspace)
            page = await context.new_page()
            await page.goto(str(request.url))
            if request.wait_for:
                await page.wait_for_selector(request.wait_for)
            download = await page.wait_for_event("download")
            target = workspace / (request.target_path or request.filename or download.suggested_filename or f"{uuid.uuid4()}")
            target.parent.mkdir(parents=True, exist_ok=True)
            await download.save_as(str(target))
            downloads.append(str(target))
            return TaskResult(status="ok", telemetry={"url": str(request.url)}, artifacts=downloads)
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
