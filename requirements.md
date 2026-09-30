# Requirements Document

## Introduction

The Haulage Event Simulator is a standalone web application that generates and
publishes `HaulageVehicleIntegrationEvent` messages onto the SmartFlow RabbitMQ
event bus. In production these events originate from external hardware
(reader/WiFi edge gateways) that are not part of this workspace. The simulator
fills that gap: an operator selects a target SmartFlow server, authenticates,
picks live entities (vehicles, beacons, employees) from dropdowns fed by the
SmartFlow APIs, and publishes events that `Haulages.API` processes identically to
those from real hardware.

The application runs 24/7 on a Linux server and continuously monitors the event
bus for incoming haulage events. When a user logs in they receive a summary of
all events that arrived since their last session — enabling the primary workflow:
a real vehicle sends a Load event then goes offline; the operator sees this via
the Simulator and continues simulating the WeighingMachine and Unload events for
that vehicle.

---

## Glossary

- **Simulator**: The Haulage Event Simulator web application, comprising a Python
  backend and a React frontend served as a single deployable unit.
- **Event_Bus**: The RabbitMQ exchange named `smartflow_event_bus` (type `direct`)
  used by SmartFlow microservices to exchange integration events.
- **SmartFlow_API**: The collective HTTP REST APIs exposed by the SmartFlow
  microservices on a given server (Haulages.API, Catalog.API, Wrapper.API,
  Identity.API).
- **Identity_API**: The SmartFlow Identity microservice that authenticates users
  and issues OAuth2/OIDC Bearer_Tokens.
- **Haulages_API**: The SmartFlow microservice that consumes
  `HaulageVehicleIntegrationEvent` messages and manages haulage business logic.
- **Catalog_API**: The SmartFlow microservice that owns Vehicle, Beacon, Employee,
  and SmartFlowTag master data.
- **Wrapper_API**: The SmartFlow microservice that accepts location data via HTTP
  and writes `LocationVehicle` documents to RethinkDB.
- **Server_Profile**: A named set of connection parameters (API base URL, RabbitMQ
  host/port/username/password/vhost, RethinkDB host/port, Redis host/port)
  defined exclusively in the Simulator's configuration file.
- **Session**: An active use period that begins when a user authenticates with
  SmartFlow credentials and ends when the user logs out or the Bearer_Token
  expires.
- **Bearer_Token**: An OAuth2 access token issued by Identity_API during
  authentication, used to authorize all SmartFlow_API calls within a Session.
- **HaulageVehicleIntegrationEvent**: The RabbitMQ integration event with fields
  `Id` (Guid), `CreationDate` (DateTime UTC), `EventId` (numeric string),
  `MACVehicle`, `Status` (StatusHaulageVehicle), `DateStatus` (DateTime UTC),
  `MACBeacon`, `MACOperator` (optional), and `RealTime` (bool), consumed by
  Haulages_API to drive haulage record creation.
- **StatusHaulageVehicle**: Enum with values WeighingMachine=0, Load=1, Unload=2,
  InTransit=3, Stop=4.
- **EventId_Counter**: A numeric counter maintained by the Simulator per Session,
  used to generate unique, incrementing EventId values assigned to published
  events.
- **Event_Log**: The Simulator's local database table that stores every event
  published by the Simulator (the outbound record).
- **Event_Feed**: The Simulator's local database table that stores every
  `HaulageVehicleIntegrationEvent` received from the Event_Bus, from any source
  (hardware or Simulator itself).
- **Monitor**: The Simulator's background component that maintains a continuous
  RabbitMQ subscription to the Event_Bus, independent of any active Session.
- **LocationVehicle**: A RethinkDB document representing the current location of a
  vehicle tag, written by Wrapper_API and observed by Haulages_API's
  `OnLocationVehicleUnloadObserver`.
- **Online_Mode**: Simulation mode where `RealTime=true` and `DateStatus` is set
  to the current UTC timestamp at publication time.
- **Offline_Mode**: Simulation mode where `RealTime=false` and the user provides a
  past `DateStatus` value.
- **MACVehicle**: The uppercase SwarmId of a Vehicle's SmartFlowTag, used as the
  vehicle identifier in a HaulageVehicleIntegrationEvent.
- **MACBeacon**: The uppercase MAC address of a Beacon that maps via
  `ReferencePointId` to a HaulageSite (Load or Unload type) or a WeighingMachine.
- **MACOperator**: The uppercase SwarmId or BluetoothAddress of an Employee's
  SmartFlowTag, used as the optional operator identifier in a
  HaulageVehicleIntegrationEvent.
- **SimulatedEnabled**: A boolean flag on a WeighingMachine configuration in
  Haulages_API that, when true, causes Haulages_API to use the vehicle's loading
  capacity instead of a live weight reading.
- **Haulage_Cycle**: The ordered sequence Load -> WeighingMachine (optional) ->
  Unload for a single vehicle that results in a Haulage record in Haulages_API.

---

## Requirements

### Requirement 1: Server Profile Management

**User Story:** As an operator, I want to select which SmartFlow server to target from the UI, so that I can simulate events against different environments (e.g., staging, production) without editing any configuration files.

#### Acceptance Criteria

1. WHEN the Simulator starts, THE Simulator SHALL load all Server_Profiles from the configuration file.
2. IF the configuration file is absent, contains a syntax error, or contains zero Server_Profiles at startup, THEN THE Simulator SHALL log an error message indicating the file path and the reason for failure and SHALL refuse to start.
3. THE Simulator SHALL present all loaded Server_Profiles as selectable options in the UI.
4. WHEN a user selects a Server_Profile, THE Simulator SHALL use that profile's connection parameters for all SmartFlow_API calls, Event_Bus publishing, RethinkDB writes, and Monitor subscriptions.
5. THE Simulator SHALL NOT provide a UI for creating, editing, or deleting Server_Profiles.
6. WHEN a user selects a Server_Profile different from the currently active Server_Profile, THE Simulator SHALL discard the current authenticated Session and all associated session state.
7. IF no authenticated Session exists after a Server_Profile is selected, THEN THE Simulator SHALL require the user to authenticate before any SmartFlow_API calls or event publications are permitted.
8. IF the Simulator cannot establish a connection to a selected Server_Profile's RabbitMQ or SmartFlow_API when a simulation action is attempted, THEN THE Simulator SHALL display an error message identifying which connection failed and SHALL NOT publish the event.

---

### Requirement 2: SmartFlow Authentication

**User Story:** As an operator, I want to authenticate using my SmartFlow credentials, so that I can access live entity data and have my simulation actions recorded under my identity.

#### Acceptance Criteria

1. WHEN a user submits a SmartFlow username and password, THE Simulator SHALL forward those credentials to the Identity_API of the selected Server_Profile to obtain a Bearer_Token.
2. WHEN Identity_API returns a Bearer_Token, THE Simulator SHALL store the token in the active Session and use it for all subsequent SmartFlow_API requests.
3. THE Simulator SHALL NOT persist the SmartFlow password in any storage medium after the authentication request completes.
4. IF Identity_API returns an authentication failure, THEN THE Simulator SHALL display the failure reason to the user; IF Identity_API returns no reason string, THE Simulator SHALL display a generic authentication failure message.
5. IF a Bearer_Token expires or a SmartFlow_API call returns an authentication error, THEN THE Simulator SHALL display a notification to the user and SHALL require re-authentication before further SmartFlow_API calls or event publications are permitted.
6. WHEN a user logs out or explicitly closes the Session, THE Simulator SHALL discard the Bearer_Token from server-side session storage.
7. WHILE a Session is active, THE Simulator SHALL record the SmartFlow username of that Session in every Event_Log record produced during that Session.
8. IF the Identity_API authentication request does not complete within 10 seconds, THEN THE Simulator SHALL display a timeout error to the user and SHALL NOT create a Session.

---

### Requirement 3: Entity Data Loading

**User Story:** As an operator, I want the Simulator to populate dropdowns with live entity data from the selected server, so that I can pick valid vehicles, beacons, and employees without entering raw MAC addresses manually.

#### Acceptance Criteria

1. WHEN a Server_Profile is activated, IF an active Session exists, THE Simulator SHALL fetch Vehicles, Employees, Beacons, HaulageSites, and WeighingMachines from the SmartFlow_API using the active Bearer_Token, treating any individual request that does not complete within 30 seconds as a failed call.
2. THE Simulator SHALL exclude from the Vehicles dropdown any Vehicle that does not have an associated HaulageVehicle record or whose type is not 4 or 5.
3. THE Simulator SHALL exclude from the Employees dropdown any Employee that does not have at least one SmartFlowTag where either SwarmId or BluetoothAddress is a non-null, non-empty string.
4. THE Simulator SHALL exclude from the Beacons dropdown any Beacon that does not map via ReferencePointId to a HaulageSite or a WeighingMachine.
5. IF any SmartFlow_API call fails during entity loading, THEN THE Simulator SHALL display an error message identifying the entity type(s) that failed to load.
6. IF any SmartFlow_API call fails during entity loading, THEN THE Simulator SHALL retain any successfully loaded entities in their respective dropdowns without clearing them.
7. IF any SmartFlow_API call fails during entity loading, THEN THE Simulator SHALL present a retry control that restarts the full entity loading sequence.
8. WHEN a user switches to a different Server_Profile, THE Simulator SHALL discard all previously loaded entities and reload from the new profile's SmartFlow_API.

---

### Requirement 4: EventId Generation

**User Story:** As a system, every published event must carry a unique, ordered EventId so that Haulages_API can sort and process a burst of events correctly.

#### Acceptance Criteria

1. WHEN a Session starts, THE Simulator SHALL initialise an EventId_Counter at 1.
2. WHEN the Simulator publishes a HaulageVehicleIntegrationEvent, THE Simulator SHALL assign the current EventId_Counter value as the event's EventId field and then increment the counter by 1.
3. THE Simulator SHALL serialise EventId as a numeric string (e.g., "1", "42").
4. WHILE a Session is active, THE Simulator SHALL NOT assign the same EventId value to two different events.

---

### Requirement 5: Duplicate Event Prevention

**User Story:** As an operator, I want the Simulator to prevent me from accidentally publishing a duplicate event, so that Haulages_API's SHA-256 deduplication check does not silently discard a valid intended event.

#### Acceptance Criteria

1. WHEN a HaulageVehicleIntegrationEvent is successfully published, THE Simulator SHALL record the combination of (DateStatus truncated to second-level precision, MACVehicle, Status) in the Session published-combinations set.
2. WHEN a user attempts to publish a HaulageVehicleIntegrationEvent, THE Simulator SHALL determine whether the combination of (DateStatus truncated to second-level precision, MACVehicle, Status) already exists in the Session published-combinations set.
3. IF the combination of (DateStatus truncated to second-level precision, MACVehicle, Status) already exists in the Session published-combinations set, THEN THE Simulator SHALL display a warning message indicating the event would be silently discarded as a duplicate by Haulages_API.
4. IF the combination of (DateStatus truncated to second-level precision, MACVehicle, Status) already exists in the Session published-combinations set, THEN THE Simulator SHALL NOT publish the event.
5. WHEN the Simulator application starts, THE Simulator SHALL initialise the Session published-combinations set as empty.

---

### Requirement 6: Online and Offline Simulation Modes

**User Story:** As an operator, I want to publish both live events and past (offline) events, so that I can reconstruct the full timeline for a vehicle that was unreachable.

#### Acceptance Criteria

1. THE Simulator SHALL require the user to select either Online_Mode or Offline_Mode for each event, and SHALL disable the Publish action until a mode is selected.
2. WHEN a user publishes an event in Online_Mode, THE Simulator SHALL set RealTime=true and SHALL system-assign DateStatus to the current UTC timestamp at the moment of publication.
3. WHEN a user publishes an event in Offline_Mode, THE Simulator SHALL set RealTime=false and SHALL require the user to provide a DateStatus value as a UTC date-time.
4. IF the DateStatus value provided in Offline_Mode is not strictly before the current UTC timestamp at the moment of publication, THEN THE Simulator SHALL display a validation error and SHALL NOT publish the event.
5. WHILE Online_Mode is selected, THE Simulator SHALL disable the DateStatus input field.

---

### Requirement 7: Load Event Simulation

**User Story:** As an operator, I want to simulate a vehicle tag read at a load beacon, so that Haulages_API opens a Haulage_Cycle for that vehicle.

#### Acceptance Criteria

1. WHEN a user selects a vehicle and a Beacon mapped to a Load-type HaulageSite and triggers a Load simulation, THE Simulator SHALL publish a HaulageVehicleIntegrationEvent with Status=1 (Load) to the Event_Bus exchange smartflow_event_bus using routing key HaulageVehicleIntegrationEvent.
2. THE Simulator SHALL set MACVehicle to the uppercase SwarmId of the selected vehicle's SmartFlowTag; IF the SmartFlowTag has no SwarmId, THEN THE Simulator SHALL set MACVehicle to the uppercase BluetoothAddress of that SmartFlowTag.
3. THE Simulator SHALL set MACBeacon to the uppercase MAC address of the selected load Beacon.
4. WHERE an Employee is selected, THE Simulator SHALL set MACOperator to the uppercase SwarmId of that Employee's SmartFlowTag; IF the SmartFlowTag has no SwarmId, THEN THE Simulator SHALL set MACOperator to the uppercase BluetoothAddress of that SmartFlowTag.
5. THE Simulator SHALL set the base Id field to a newly generated Guid and CreationDate to the current UTC timestamp.
6. WHEN the event is published successfully, THE Simulator SHALL write a record to the Event_Log.
7. IF the selected vehicle has no SmartFlowTag OR the SmartFlowTag has neither SwarmId nor BluetoothAddress, THEN THE Simulator SHALL prevent the Load simulation from being triggered and display an error message indicating the vehicle has no addressable tag.
8. WHERE no Employee is selected, THE Simulator SHALL set MACOperator to an empty string.
9. IF publishing the HaulageVehicleIntegrationEvent to the Event_Bus fails, THEN THE Simulator SHALL display an error message indicating the publish failure and SHALL NOT write a record to the Event_Log.

---

### Requirement 8: Unload Event Simulation

**User Story:** As an operator, I want to simulate a vehicle tag read at an unload beacon, so that Haulages_API closes the Haulage_Cycle and creates a Haulage record.

#### Acceptance Criteria

1. WHEN a user selects a vehicle and a Beacon mapped to an Unload-type HaulageSite (from a Beacons list pre-filtered to Unload-type mappings) and triggers an Unload simulation, THE Simulator SHALL publish a HaulageVehicleIntegrationEvent with Status=2 (Unload) to the Event_Bus.
2. THE Simulator SHALL set MACVehicle, MACBeacon, MACOperator, Id, and CreationDate following the same rules defined in Requirement 7.
3. WHEN a vehicle is selected for an Unload event, THE Simulator SHALL look up the most recent Status=1 (Load) event for that vehicle in the Event_Log for the active Server_Profile and display the elapsed time since that Load event in hours and minutes.
4. IF no Status=1 (Load) event exists in the Event_Log for the selected vehicle and active Server_Profile, THEN THE Simulator SHALL display a notice that no prior Load event was found and that Haulages_API may not create a Haulage record.
5. IF the elapsed time since the most recent Status=1 (Load) event for the selected vehicle exceeds 18 hours, THEN THE Simulator SHALL display a warning that Haulages_API will not create a Haulage record due to the 18-hour rule.
6. WHEN the event is published successfully, THE Simulator SHALL write a record to the Event_Log.
7. IF publishing the HaulageVehicleIntegrationEvent to the Event_Bus fails, THEN THE Simulator SHALL display an error message indicating the publish failure and SHALL NOT write a record to the Event_Log.

---

### Requirement 9: WeighingMachine Event Simulation

**User Story:** As an operator, I want to simulate a vehicle tag read at a weighing machine beacon, so that Haulages_API captures a net weight or tare update for the current Haulage_Cycle.

#### Acceptance Criteria

1. WHEN a user selects a vehicle and a Beacon mapped to a WeighingMachine and triggers a WeighingMachine simulation, THE Simulator SHALL publish a HaulageVehicleIntegrationEvent with Status=0 (WeighingMachine) to the Event_Bus.
2. THE Simulator SHALL offer two weighing modes for WeighingMachine events: Standard and SimulatedEnabled.
3. WHILE the weighing mode is Standard, THE Simulator SHALL require the user to enter a gross weight value in tonnes greater than 0 and no greater than 999.99 before the event can be published.
4. WHILE the weighing mode is Standard, THE Simulator SHALL write the user-provided weight value to the RethinkDB document for the selected WeighingMachine before publishing the HaulageVehicleIntegrationEvent, so that Haulages_API reads a stable weight during its stabilisation loop.
5. WHILE the weighing mode is SimulatedEnabled, THE Simulator SHALL publish the HaulageVehicleIntegrationEvent without writing a weight to RethinkDB, relying on the WeighingMachine's SimulatedEnabled flag already being set in Haulages_API configuration.
6. WHEN the user enters a weight value in Standard mode and the selected vehicle has a defined EmptyWeight, THE Simulator SHALL compute abs(entered_weight - vehicle.EmptyWeight) and display whether the reading will be processed as a net load (difference > 2.5 t) or a tare update (difference <= 2.5 t) by Haulages_API.
7. WHEN the event is published successfully, THE Simulator SHALL write a record to the Event_Log containing the UTC publication timestamp, vehicle identifier, beacon identifier, weighing mode, and gross weight (for Standard mode).
8. IF the selected vehicle does not have a defined EmptyWeight, THEN THE Simulator SHALL suppress the net load/tare classification display and indicate that EmptyWeight is unavailable.
9. IF the RethinkDB write in Standard mode fails, THEN THE Simulator SHALL display an error message and SHALL NOT publish the HaulageVehicleIntegrationEvent.
10. IF publishing the HaulageVehicleIntegrationEvent to the Event_Bus fails, THEN THE Simulator SHALL display an error message and SHALL NOT write a record to the Event_Log.

---

### Requirement 10: InTransit and Stop Event Simulation

**User Story:** As an operator, I want to simulate vehicle movement status events, so that Haulages_API monitor views correctly reflect a vehicle's transit state.

#### Acceptance Criteria

1. WHEN a user selects a vehicle and triggers an InTransit simulation, THE Simulator SHALL publish a HaulageVehicleIntegrationEvent with Status=3 (InTransit) to the Event_Bus.
2. WHEN a user selects a vehicle and triggers a Stop simulation, THE Simulator SHALL publish a HaulageVehicleIntegrationEvent with Status=4 (Stop) to the Event_Bus.
3. WHEN an InTransit or Stop simulation is triggered, THE Simulator SHALL set MACVehicle, Id, and CreationDate following the same rules defined in Requirement 7.
4. WHEN the event is published successfully, THE Simulator SHALL write a record to the Event_Log containing the vehicle identifier, event Status value, and UTC publication timestamp.
5. IF publishing fails when an InTransit or Stop event is triggered, THEN THE Simulator SHALL display an error message and SHALL NOT write a record to the Event_Log.
6. IF no vehicle is selected when an InTransit or Stop simulation is triggered, THEN THE Simulator SHALL display an error requiring a vehicle to be selected and SHALL NOT publish the event.

---

### Requirement 11: Location-Based Unload Simulation

**User Story:** As an operator, I want to simulate a vehicle location change that triggers Haulages_API's location observer, so that I can test the alternative unload path that does not require an explicit Unload event.

#### Acceptance Criteria

1. WHEN a user selects a vehicle (type 4 or 5) and an Unload-type HaulageSite and triggers a location-based unload simulation, THE Simulator SHALL send an HTTP POST request to the Wrapper_API location endpoint of the active Server_Profile.
2. WHEN a location-based unload simulation is triggered, THE Simulator SHALL populate the LocationVehicle payload with the selected vehicle's unique identifier, the ReferencePointId of the selected Unload-type HaulageSite, and an isUsedLocation value of true.
3. WHEN a location-based unload simulation is triggered, THE Simulator SHALL include the active Bearer_Token in the Authorization header of the Wrapper_API request.
4. IF the Wrapper_API request returns an error response, THEN THE Simulator SHALL display the error to the user and SHALL NOT record the simulation as successful in the Event_Log.
5. WHEN the Wrapper_API request returns a success response, THE Simulator SHALL write a record to the Event_Log containing the simulation type "LocationBasedUnload", the selected vehicle's unique identifier, the selected HaulageSite's identifier, and the UTC timestamp of the request.

---

### Requirement 12: Operator Assignment Simulation

**User Story:** As an operator, I want to simulate a WiFi operator assignment event, so that Haulages_API associates an employee with a vehicle and includes them on haulage records.

#### Acceptance Criteria

1. WHEN a user selects a vehicle with a non-empty MACVehicle and an Employee with a non-empty MACOperator and triggers an operator assignment simulation, THE Simulator SHALL publish a CatalogVehicleOperatorAssignmentEvent to the Event_Bus with VehicleMAC set to the vehicle's MACVehicle and OperatorMAC set to the employee's MACOperator.
2. WHEN a CatalogVehicleOperatorAssignmentEvent is published, THE Simulator SHALL use the Event_Bus exchange smartflow_event_bus with routing key CatalogVehicleOperatorAssignmentEvent.
3. WHEN the event is published successfully, THE Simulator SHALL write a record to the Event_Log containing the event name, VehicleMAC, OperatorMAC, and UTC publication timestamp.
4. IF the Event_Bus is unavailable or the publish fails, THEN THE Simulator SHALL display an error message and SHALL NOT write a record to the Event_Log.
5. IF either MACVehicle or MACOperator is absent when an operator assignment is triggered, THEN THE Simulator SHALL prevent publication and display an error message identifying which MAC is missing.

---

### Requirement 13: Continuous Event Monitoring

**User Story:** As an operator, I want the Simulator to capture all HaulageVehicleIntegrationEvents on the bus -- including those from real hardware -- so that I can see what happened since my last session and decide which follow-up events to simulate.

#### Acceptance Criteria

1. THE Monitor SHALL maintain a durable queue on the smartflow_event_bus exchange, bound with routing key HaulageVehicleIntegrationEvent, regardless of whether any user Session is active.
2. WHEN the Monitor receives a HaulageVehicleIntegrationEvent, THE Simulator SHALL store the message body as received and the UTC receipt timestamp in the Event_Feed, and SHALL acknowledge the message to the Event_Bus only after the record is successfully persisted.
3. THE Simulator SHALL mark each Event_Feed record to indicate whether the event originated from the Simulator itself or from an external source.
4. THE Simulator SHALL persist Event_Feed records in the local database so that they survive Simulator process restarts.
5. WHEN the Monitor's RabbitMQ connection is lost, THE Simulator SHALL attempt to reconnect with a retry interval between 5 and 30 seconds until the connection is restored.
6. IF persisting an Event_Feed record fails, THEN THE Simulator SHALL NOT acknowledge the message to the Event_Bus, allowing the broker to redeliver it.

---

### Requirement 14: Login Event Summary

**User Story:** As an operator, I want to see a summary of haulage events that occurred since my last login, so that I can quickly identify vehicles that need a follow-up simulation.

#### Acceptance Criteria

1. WHEN a user completes authentication successfully, THE Simulator SHALL record the current UTC timestamp as the last_seen value for that SmartFlow username, overwriting any existing value.
2. WHEN a user completes authentication successfully, THE Simulator SHALL retrieve all Event_Feed records with a receipt timestamp strictly after that user's previous last_seen timestamp.
3. WHEN the post-login Event_Feed retrieval returns one or more records, THE Simulator SHALL display them as a post-login summary grouped by MACVehicle, ordered by MACVehicle ascending.
4. IF no previous last_seen timestamp exists for a username, THE Simulator SHALL retrieve Event_Feed records with a receipt timestamp within the 24 hours immediately preceding the authentication timestamp.
5. IF the post-login Event_Feed retrieval returns no records, THE Simulator SHALL display a message indicating no new haulage events since the last login.
6. IF recording the last_seen timestamp fails after successful authentication, THE Simulator SHALL present an error indication to the user without blocking access to the post-login summary.

---

### Requirement 15: Simulation Audit Log

**User Story:** As a team lead, I want a searchable history of every simulated event, so that I can audit who triggered each simulation and reproduce reported issues.

#### Acceptance Criteria

1. WHEN the Simulator publishes any event, THE Simulator SHALL write a record to the Event_Log containing: publication timestamp (UTC), SmartFlow username, Server_Profile name, event type (Status value or "LocationBasedUnload" or "OperatorAssignment"), MACVehicle, MACBeacon (null where not applicable), MACOperator (null where not applicable), simulation mode (Online_Mode or Offline_Mode), and the full JSON payload of the published message.
2. THE Simulator SHALL retain Event_Log records indefinitely and SHALL NOT automatically delete them.
3. THE Simulator SHALL provide a UI view that lists Event_Log records filtered by the AND combination of: SmartFlow username, MACVehicle, date range (UTC, date-and-time precision, both bounds inclusive), and event type; unset filters SHALL match all records.
4. THE Simulator SHALL display Event_Log records in reverse chronological order by default.
5. WHILE the number of matching Event_Log records exceeds 100, THE Simulator SHALL paginate results in pages of 100 and display the total match count with navigation controls.
6. IF no Event_Log records match the active filters, THE Simulator SHALL display an empty list and an explanatory message.
7. IF writing an Event_Log record fails, THE Simulator SHALL display an error notification and SHALL NOT abort the event publication.

---

### Requirement 16: RabbitMQ Reconnection

**User Story:** As an operator, I want the Simulator to recover automatically from RabbitMQ connection failures, so that the Monitor misses no events and simulation publishing resumes without manual intervention.

#### Acceptance Criteria

1. WHEN the Monitor's RabbitMQ connection is lost, THE Simulator SHALL attempt to reconnect using exponential backoff, starting at a 2-second interval and doubling up to a maximum of 60 seconds between attempts.
2. WHEN a reconnection succeeds, THE Simulator SHALL re-declare and re-bind the durable subscription queue to the Event_Bus, resume consuming messages including any messages queued during the disconnection period, and update the connection-status indicator to reflect the restored connection.
3. WHEN a reconnection attempt is made, THE Simulator SHALL log the attempt timestamp and its outcome.
4. WHILE the Monitor is disconnected from RabbitMQ, THE Simulator SHALL display an indicator in the application interface that identifies the RabbitMQ connection as unavailable.
5. IF the publishing channel is unavailable when a user triggers an event publication and is not restored within 10 seconds, THEN THE Simulator SHALL display an error message to the user and SHALL discard the pending event.
6. IF the publishing channel is restored within 10 seconds of a triggered event publication, THEN THE Simulator SHALL publish the event automatically without requiring the user to re-trigger it.

---

### Requirement 17: Deployment and Runtime

**User Story:** As a system administrator, I want the Simulator to run natively on Linux as a single self-contained process, so that I can deploy it without Docker or container orchestration.

#### Acceptance Criteria

1. THE Simulator SHALL run as a Python process natively on Linux without requiring Docker or any container runtime.
2. THE Simulator SHALL serve the compiled React frontend as static files from the same HTTP server process that exposes the backend API, requiring no additional server process.
3. WHILE the Simulator is running, THE Monitor SHALL maintain its RabbitMQ subscription regardless of whether any user Sessions are active.
4. THE Simulator SHALL read all Server_Profile configuration exclusively from a configuration file; no profile data SHALL be stored in the local database.
5. THE Simulator SHALL support a minimum of 10 simultaneous user Sessions accessing the shared Event_Feed and Event_Log concurrently without data loss or inconsistency between Sessions.
6. WHEN the Monitor's RabbitMQ subscription drops, THE Simulator SHALL attempt automatic reconnection with a maximum retry interval of 30 seconds.
7. IF the configuration file is absent or malformed at startup, THEN THE Simulator SHALL log an error message identifying the file path and reason and SHALL refuse to start.

---

### Requirement 18: Data Security

**User Story:** As a security-conscious administrator, I want the Simulator to handle SmartFlow credentials safely and avoid unauthorized data modifications, so that it poses minimal risk to the SmartFlow environment.

#### Acceptance Criteria

1. THE Simulator SHALL NOT persist SmartFlow passwords in any storage medium (database, log file, or configuration file).
2. THE Simulator SHALL NOT provide a UI for user account management, password resets, or role assignment.
3. THE Simulator SHALL NOT perform direct data interactions, including reads and writes, against SmartFlow's relational databases; all SmartFlow data interactions SHALL be performed exclusively via SmartFlow_API HTTP endpoints or Event_Bus message publication.
4. THE Simulator SHALL transmit SmartFlow credentials to Identity_API exclusively over HTTPS.
5. THE Simulator SHALL store Bearer_Tokens in server-side session storage only; Bearer_Tokens SHALL NOT be written to the local database or any persistent file, and SHALL be cleared from session storage upon session termination.
6. IF an HTTPS connection to Identity_API cannot be established during authentication, THEN THE Simulator SHALL display an error message and SHALL NOT attempt to transmit credentials over an unencrypted connection.
