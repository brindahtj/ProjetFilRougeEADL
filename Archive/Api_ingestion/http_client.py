import logging
from typing import Optional, Dict, Any

import requests

from Archive.Api_ingestion.exceptions import ApiClientError

log = logging.getLogger(__name__)


class HttpClient:
    """
    Client HTTP simple et réutilisable.
    Encapsule les appels réseau et la gestion d'erreurs.
    """

    def __init__(self, base_url: str, timeout: int = 10):
        """
        Args:
            base_url: URL de base de l'API
            timeout: Timeout des requêtes en secondes
        """
        self.base_url = base_url
        self.timeout = timeout

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        error_message: str = "Erreur HTTP",
    ) -> Dict[str, Any]:
        """
        Effectue une requête GET.

        Args:
            endpoint: Chemin relatif (ex: "/locations")
            params: Paramètres de la requête
            error_message: Message d'erreur personnalisé

        Returns:
            Réponse JSON en dict

        Raises:
            ApiClientError: En cas d'erreur réseau
        """
        url = f"{self.base_url}{endpoint}" if endpoint else self.base_url

        try:
            log.debug(f"GET {url} avec params {params}")
            response = requests.get(
                url,
                params=params or {},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as exc:
            raise ApiClientError(
                f"{error_message} : Timeout après {self.timeout}s",
                context="HTTP_TIMEOUT"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ApiClientError(
                f"{error_message} : Erreur de connexion",
                context="HTTP_CONNECTION"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise ApiClientError(
                f"{error_message} : HTTP {exc.response.status_code}",
                context="HTTP_STATUS"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ApiClientError(
                f"{error_message} : {exc}",
                context="HTTP_ERROR"
            ) from exc
        except ValueError as exc:
            raise ApiClientError(
                f"{error_message} : Réponse JSON invalide",
                context="JSON_PARSE"
            ) from exc