from fastapi import Request

from watchapi.finders import Finder
from watchapi.hub import ScanHub
from watchapi.store import WatchStore


def get_store(request: Request) -> WatchStore:
    return request.app.state.store


def get_finder(request: Request) -> Finder:
    return request.app.state.finder


def get_hub(request: Request) -> ScanHub:
    return request.app.state.hub
