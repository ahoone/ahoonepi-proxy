import asyncio
import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import ipaddress
import nodriver as uc
import random
from typing import Optional, List, Dict


# TO DO :
# - refusing cookies ?
# - clicking on a link (button) if a target link is given
# - browse back in history
# - having a way to input a specified lifespan for a browser (so far it is always the default one)


# -------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------- #


LIFESPAN_BROWSER = 1 # in hours
PAGE_LOADING_UNIFORM_RANGE = (2, 4) # in seconds
PAGE_SCROLLING_UNIFORM_RANGE = (200, 400) # 100 <=> height of the browser window
PERIOD_CLEANUP_LOOP = 300 # in seconds


# -------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------- #


ALLOWED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # localhost
    ipaddress.ip_network("10.0.0.0/24"),      # VPN network
    ipaddress.ip_network("172.16.0.0/12"),    # Docker bridge networks (for dev)
    ipaddress.ip_network("::1/128"),          # IPv6 localhost
]


app = FastAPI(
    title="Scraper API",
    description="Scraper",
    version="1.0.0"
)


@app.get("/check-ip")
async def check_ip(request: Request):
    """Check what IP the server sees and if it's allowed"""
    client_ip = request.client.host
    
    # Check proxy headers too
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    x_real_ip = request.headers.get("X-Real-IP")
    
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        
        # Check against each network
        network_checks = {}
        for network in ALLOWED_NETWORKS:
            is_in_network = client_ip_obj in network
            network_checks[str(network)] = is_in_network
        
        # Overall allowed status
        allowed = any(client_ip_obj in network for network in ALLOWED_NETWORKS)
        
        return {
            "received_ip": client_ip,
            "x_forwarded_for": x_forwarded_for,
            "x_real_ip": x_real_ip,
            "is_allowed": allowed,
            "network_checks": network_checks,
            "allowed_networks": [str(net) for net in ALLOWED_NETWORKS]
        }
    except ValueError as e:
        return {
            "received_ip": client_ip,
            "x_forwarded_for": x_forwarded_for,
            "x_real_ip": x_real_ip,
            "is_allowed": False,
            "error": f"Invalid IP address: {str(e)}",
            "allowed_networks": [str(net) for net in ALLOWED_NETWORKS]
        }


@app.middleware("http")
async def filter_ip_middleware(request: Request, call_next):
    client_ip = request.client.host
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        allowed = any(client_ip_obj in network for network in ALLOWED_NETWORKS)
        if not allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Access forbidden from IP: {client_ip}"},
            )
        response = await call_next(request)
        return response
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid IP address: {client_ip}"},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------- #


class BrowserInstance:

    def __init__(
        self,
        expiration_date: datetime.datetime = None,
    ) -> None:
        self.browser = None
        self.expiration_date = expiration_date or (datetime.datetime.now() + datetime.timedelta(hours=LIFESPAN_BROWSER))
        self._initialized = False
        self.created_at = datetime.datetime.now()
        self.access_history: List[Dict] = []

    # __INIT__ CAN NOT BE ASYNC IN PYTHON
    async def initialize(self):
        """Initialize the browser (called once)"""
        if not self._initialized:
            self.browser = await uc.start(
                headless=False,                                             # If headerless, Cloudflare spots us.
                browser_args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--window-size=1920,1080',
                ],                                                          # If images are blocked, Cloudflare spots us.
                sandbox=False,
            )
            self._initialized = True
        return self


    async def scrape(self, url: str) -> str:
        """Scrape a URL using the persistent browser"""
        if not self._initialized:
            await self.initialize()

        access_record = {
            "url": url,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "in_progress"
        }

        try:
            page = await self.browser.get(url)
            await page.sleep(random.uniform(*PAGE_LOADING_UNIFORM_RANGE))
            await page.scroll_down(random.randint(*PAGE_SCROLLING_UNIFORM_RANGE))
            html_content = await page.get_content()

            access_record["status"] = "success"
            access_record["content_length"] = len(html_content)
            access_record["completed_at"] = datetime.datetime.now().isoformat()

            self.access_history.append(access_record)
            return html_content

        except Exception as e:
            access_record["status"] = "failed"
            access_record["error"] = str(e)
            access_record["completed_at"] = datetime.datetime.now().isoformat()
            self.access_history.append(access_record)
            raise


    async def close(self):
        """Explicitly close the browser"""
        if self.browser:
            await self.browser.stop()
            self._initialized = False


    def is_expired(self) -> bool:
        """Check if this instance has expired"""
        return datetime.datetime.now() > self.expiration_date


    def get_stats(self) -> Dict:
        """Get statistics about this instance"""
        total_requests = len(self.access_history)
        successful_requests = sum(1 for record in self.access_history if record["status"] == "success")
        failed_requests = sum(1 for record in self.access_history if record["status"] == "failed")
        
        return {
            "created_at": self.created_at.isoformat(),
            "expiration_date": self.expiration_date.isoformat(),
            "is_expired": self.is_expired(),
            "is_initialized": self._initialized,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "access_history": self.access_history
        }


# -------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------- #


class BrowserInstancePool:

    def __init__(self):
        self.instances: dict[str, BrowserInstance] = {}


    async def get_or_create_instance(self, instance_id: str) -> BrowserInstance:
        """Get existing instance or create new one"""
        if instance_id not in self.instances:
            instance = BrowserInstance()
            await instance.initialize()
            self.instances[instance_id] = instance

        instance = self.instances[instance_id]

        if instance.is_expired():
            await instance.close()
            instance = BrowserInstance()
            await instance.initialize()
            self.instances[instance_id] = instance

        return instance


    async def cleanup_expired(self):
        """Remove and close expired instances"""
        expired_ids = [
            instance_id for instance_id, instance in self.instances.items()
            if instance.is_expired()
        ]
        for instance_id in expired_ids:
            await self.instances[instance_id].close()
            del self.instances[instance_id]


    def get_all_stats(self) -> Dict:
        """Get stats for all instances"""
        return {
            instance_id: instance.get_stats()
            for instance_id, instance in self.instances.items()
        }


# -------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------- #


pool = BrowserInstancePool()


@app.post("/scrape")
async def scrape_endpoint(url: str, instance_id: str = "default"):
    """Scrape a URL using a persistent browser instance"""
    try:
        instance = await pool.get_or_create_instance(instance_id)
        content = await instance.scrape(url)
        return {
            "status": "success",
            "content": content,
            "instance_id": instance_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/close-instance")
async def close_instance(instance_id: str):
    """Manually close a browser instance"""
    if instance_id in pool.instances:
        stats = pool.instances[instance_id].get_stats()
        await pool.instances[instance_id].close()
        del pool.instances[instance_id]
        return {
            "status": "closed",
            "instance_id": instance_id,
            "final_stats": stats,
        }
    return {"status": "not_found", "instance_id": instance_id}


@app.get("/instances")
async def list_instances():
    """List all active instances with their access history"""
    return {
        "total_instances": len(pool.instances),
        "instances": pool.get_all_stats(),
    }


@app.get("/instance/{instance_id}")
async def get_instance_details(instance_id: str):
    """Get detailed information about a specific instance"""
    if instance_id not in pool.instances:
        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

    return {
        "instance_id": instance_id,
        **pool.instances[instance_id].get_stats(),
    }


@app.get("/instance/{instance_id}/history")
async def get_instance_history(instance_id: str):
    """Get access history for a specific instance"""
    if instance_id not in pool.instances:
        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")
    
    return {
        "instance_id": instance_id,
        "access_history": pool.instances[instance_id].access_history,
    }


@app.get("/stats")
async def get_global_stats():
    """Get global statistics across all instances"""
    all_stats = pool.get_all_stats()
    
    total_requests = sum(stats["total_requests"] for stats in all_stats.values())
    total_successful = sum(stats["successful_requests"] for stats in all_stats.values())
    total_failed = sum(stats["failed_requests"] for stats in all_stats.values())
    
    return {
        "total_instances": len(pool.instances),
        "total_requests": total_requests,
        "successful_requests": total_successful,
        "failed_requests": total_failed,
        "instances": all_stats,
    }


@app.on_event("startup")
async def startup_event():
    """Cleanup expired instances regularly"""
    async def cleanup_loop():
        while True:
            await asyncio.sleep(PERIOD_CLEANUP_LOOP)
            await pool.cleanup_expired()
    
    asyncio.create_task(cleanup_loop())
