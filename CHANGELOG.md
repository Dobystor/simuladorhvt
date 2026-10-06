# Changelog — Haulage Event Simulator

Bitácora de cambios, correcciones y mejoras realizadas sobre el proyecto,
posteriores a la implementación inicial del spec (requirements/design/tasks).

El formato de cada entrada: **fecha · tipo · descripción · motivo · archivos**.
Tipos: `fix` (corrección), `feat` (funcionalidad), `style` (visual),
`deploy` (despliegue), `chore` (mantenimiento).

---

## Despliegue inicial en servidor de pruebas (LASEC)

Contexto: el backend y frontend quedaron completos y probados en local
(65 tests). Al desplegar contra el SmartFlow real de LASEC
(`haulage-01.smartflow.com.mx`) fueron apareciendo diferencias entre lo que el
diseño asumía y el comportamiento real del servidor. Cada una se corrigió:

### 1. `deploy` — Scripts de despliegue systemd
- **Qué**: se crearon `deploy/install.sh`, `deploy/update.sh`, `deploy/run.sh` y
  `deploy/haulage-simulator.service` para correr el simulador como servicio
  Linux 24/7 sin Docker.
- **Motivo**: Requisito 17 (nativo, sin contenedores). Opción elegida por el
  usuario (systemd).
- **Archivos**: `deploy/*`

### 2. `fix` — Node 18+ y pnpm en el instalador
- **Qué**: el instalador valida Node ≥18 y documenta instalación vía NodeSource;
  los scripts se corren como usuario normal (no sudo) para usar el Node de
  fnm/nvm, usando sudo solo en pasos de sistema.
- **Motivo**: el servidor tenía Node 12 (apt) y Node 24 (fnm); correr con sudo
  no veía el Node del usuario.
- **Archivos**: `deploy/install.sh`, `deploy/update.sh`, `README.md`

### 3. `fix` — Exchange RabbitMQ `durable=false`
- **Qué**: el exchange `smartflow_event_bus` se declara con `durable=False` para
  coincidir con el broker real.
- **Motivo**: el diseño asumía `durable=true`, pero SmartFlow lo tiene como
  `durable=false`. RabbitMQ rechazaba la conexión con `PRECONDITION_FAILED`.
- **Archivos**: `backend/app/background/publisher_manager.py`,
  `backend/app/background/monitor.py`

### 4. `fix` — Autenticación OAuth con client_id/secret y scope correctos
- **Qué**: el login usa `grant_type=password` enviando `client_id`,
  `client_secret` y `scope=smartflow IdentityServerApi offline_access`, probando
  múltiples clientes en orden (`private.networking.app`, luego
  `smartflow.csharp.client`). Se agregó `verify=False` para el certificado
  self-signed de SmartFlow.
- **Motivo**: el endpoint real es `/api/openid/connect/token` (no
  `/connect/token`), y requiere client credentials. Sin ellos daba
  `invalid_client` / 302. Datos tomados del bot de referencia.
- **Archivos**: `backend/app/config.py`,
  `backend/app/services/identity_service.py`,
  `backend/app/services/entity_service.py`,
  `backend/app/services/wrapper_service.py`

### 5. `fix` — Endpoints de entidades reales + normalización PascalCase
- **Qué**: se corrigieron los endpoints a los reales del facade
  (`/service/catalog/...` y `/service/haulages/...`) y se agregó una capa de
  normalización PascalCase/camelCase → snake_case.
- **Motivo**: el diseño asumía `/api/v1/Vehicle` etc. (daban 404). La estructura
  real usa `SmartFlowTag.SwarmId` para el MAC, campos en PascalCase.
- **Archivos**: `backend/app/services/entity_service.py`,
  `backend/app/api/entities.py`

### 6. `fix` — Tolerar `reference_point_id` nulo
- **Qué**: `WeighingMachineInfo` y `HaulageSiteInfo` aceptan
  `reference_point_id` nulo; las básculas/sitios sin él se descartan.
- **Motivo**: había una báscula de prueba ("ASDDDD") con `referencePointId:null`
  que rompía la validación Pydantic de toda la respuesta.
- **Archivos**: `backend/app/models/api_models.py`, `backend/app/api/entities.py`

### 7. `style` — Tema cyber-dark de SmartFlow
- **Qué**: se replicó la identidad visual del bot de referencia (fondo oscuro
  `#111113`, acentos neón, fuentes Inter/Orbitron, header con línea de
  gradiente, cards/inputs/tabs/badges oscuros).
- **Motivo**: consistencia visual con el resto de SmartFlow. Sin cambios de
  funcionalidad.
- **Archivos**: `frontend/src/styles.css`,
  `frontend/src/components/layout/AppShell.jsx`,
  `frontend/src/pages/LoginPage.jsx`

### 8. `feat` — Selector de fecha Flatpickr
- **Qué**: se reemplazó el `datetime-local` nativo por Flatpickr (tema oscuro,
  locale español, formato 24h, salida ISO 8601).
- **Motivo**: el selector nativo era feo y daba formato ambiguo. El bot de
  referencia usa Flatpickr.
- **Archivos**: `frontend/src/components/DateTimePicker.jsx`,
  `frontend/src/components/simulate/ModeSelector.jsx`,
  `frontend/src/styles.css`, `frontend/package.json`

### 9. `fix` — Sufijo `Z` en `date_status` entrante (Python 3.10)
- **Qué**: al recibir `date_status` del frontend, se normaliza el sufijo `Z` a
  `+00:00` antes de parsear con `datetime.fromisoformat`.
- **Motivo**: Python 3.10 (del servidor) no acepta el `Z` en `fromisoformat`
  (soporte llegó en 3.11). El local tenía 3.13, por eso no se detectó antes.
- **Archivos**: `backend/app/api/simulate.py`

### 10. `fix` — Fechas con `Z` al publicar (compatibilidad .NET)
- **Qué**: `DateStatus` y `CreationDate` se serializan con sufijo `Z` en vez de
  `+00:00`.
- **Motivo**: Haulages.API (.NET) llama `ConvertTimeFromUtc`, que exige
  `DateTimeKind.Utc`. Con `+00:00` lo interpretaba como no-UTC y lanzaba
  `ArgumentException`.
- **Archivos**: `backend/app/services/event_constructor.py`

### 11. `feat` — Refresh automático del token (sin re-login)
- **Qué**: al login se guardan `refresh_token` + credenciales de cliente. Si una
  llamada a la API da 401, el backend refresca el token con el `refresh_token` y
  reintenta de forma transparente. Solo si el refresh falla se pide re-login.
- **Motivo**: el token de SmartFlow expira (~30 min) y las entidades dejaban de
  cargar con 401. Ahora la sesión se mantiene hasta logout manual.
- **Archivos**: `backend/app/session_store.py`,
  `backend/app/services/identity_service.py`,
  `backend/app/services/token_refresh.py`, `backend/app/api/auth.py`,
  `backend/app/api/entities.py`

---

### 12. `feat` — Entrada manual de MAC + indicador de vehículos/operadores sin tag
- **Qué**:
  - Toggle "Enter MACs manually" en los paneles de simulación: permite escribir
    directamente el MAC de vehículo, beacon y operador en vez de seleccionarlos
    de los dropdowns.
  - Los dropdowns ahora marcan con "⚠ NO TAG" / "⚠ no tag" los vehículos y
    operadores que no tienen SmartFlowTag asignado, en lugar de ocultarlos u
    fallar hasta el momento de publicar.
  - El backend resuelve el MAC de cada vehículo/empleado y expone los campos
    `mac` y `has_tag`; ya no se filtran silenciosamente los que no tienen tag.
- **Motivo**: solicitado por el usuario — poder enviar eventos por MAC directo
  y saber de antemano qué entidades no tienen tag.
- **Archivos**: `backend/app/models/api_models.py`,
  `backend/app/services/entity_service.py`, `backend/app/api/entities.py`,
  `frontend/src/store/appStore.js`,
  `frontend/src/components/simulate/EntitySelectors.jsx`,
  `frontend/src/components/simulate/useResolvedMacs.js`,
  `frontend/src/components/simulate/{Load,Unload,Weighing,InTransitStop,OperatorAssign}Panel.jsx`

### 13. `feat` — Servidores dinámicos desde la UI (multi-server)
- **Qué**: se pueden agregar/eliminar servidores SmartFlow desde la pantalla de
  login, sin editar `config.yaml`. Los servidores se guardan en SQLite
  (`server_config`), y al agregarlos se arrancan automáticamente su Monitor y
  Publisher. Al eliminarlos se detienen. `config.yaml` se vuelve opcional.
- **Motivo**: el usuario quiere conectar a distintos servidores (ej. `.39` y
  `.16`) desde un solo deployment, sin tocar archivos de configuración.
- **Archivos**: `backend/app/database.py`, `backend/app/api/servers.py`,
  `backend/app/api/auth.py`, `backend/app/api/entities.py`,
  `backend/app/api/simulate.py`, `backend/app/main.py`,
  `frontend/src/components/auth/ProfileSelector.jsx`

### 14. `feat` — Toggle manual/catálogo por campo independiente
- **Qué**: cada campo (Vehicle, Beacon, Operator) tiene su propio checkbox
  "Manual" que alterna entre el dropdown del catálogo y un campo de texto para
  escribir el MAC. Se pueden mezclar: ej. vehículo del catálogo + beacon manual.
- **Motivo**: el toggle global anterior era todo-o-nada. El usuario pidió
  poder elegir por campo.
- **Archivos**: `frontend/src/store/appStore.js`,
  `frontend/src/components/simulate/EntitySelectors.jsx`,
  `frontend/src/components/simulate/useResolvedMacs.js`

### 15. `feat` — Botón "Sync catalogs"
- **Qué**: botón en la página de simulación que recarga vehículos, beacons y
  operadores desde SmartFlow (vía `POST /api/entities/reload`), más un contador
  de entidades cargadas. Útil cuando se crean entidades nuevas en SmartFlow.
- **Motivo**: solicitado — poder refrescar el catálogo sin re-loguearse.
- **Archivos**: `frontend/src/pages/SimulatePage.jsx`

### 16. `feat` — Selectores con buscador
- **Qué**: nuevo componente `SearchableSelect` (combobox con búsqueda al
  escribir, tema oscuro). Reemplaza los `<select>` nativos de vehículo, beacon,
  operador y sitio en los paneles de simulación.
- **Motivo**: solicitado — con muchas entidades, filtrar escribiendo es más ágil.
- **Archivos**: `frontend/src/components/SearchableSelect.jsx`,
  `frontend/src/components/simulate/EntitySelectors.jsx`,
  `frontend/src/components/simulate/LocationUnloadPanel.jsx`

## Pendientes / solicitados

_(ninguno pendiente por ahora — se irán agregando aquí conforme los pidas)_

---

## Notas de hallazgos del SmartFlow real (LASEC)

Datos descubiertos durante el despliegue, útiles para referencia:

- **Identity token endpoint**: `/api/openid/connect/token`
- **OAuth**: `grant_type=password`, `client_id=private.networking.app`,
  `scope=smartflow IdentityServerApi offline_access`
- **RabbitMQ**: `localhost:5672`, user `smartflow`, exchange
  `smartflow_event_bus` (direct, **durable=false**)
- **RethinkDB driver**: puerto host `28115` (el 28015 host → 8080 web)
- **Endpoints de entidades**:
  - Vehicles (con tag): `/service/catalog/api/v1/vehicles/all`
  - HaulageVehicles: `/service/haulages/api/v2/generalsettings/vehicles/all`
  - Employees: `/service/catalog/api/v1/employees/all`
  - Beacons: `/service/catalog/api/v1/beacons/all`
  - HaulageSites: `/service/haulages/api/v2/HaulageSites/all`
  - WeighingMachines: `/service/haulages/api/v2/weighingmachines/all`
- **Reglas de negocio Haulages.API** observadas:
  - No guarda material si el sitio de Unload es de extracción
    (`isExtraction=true`).
  - `HaulageSite.siteType`: 0=Load, 1=Unload.
