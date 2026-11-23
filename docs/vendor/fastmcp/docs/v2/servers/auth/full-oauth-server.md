> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Full OAuth Server

> Build a self-contained authentication system where your FastMCP server manages users, issues tokens, and validates them.

New in version `2.11.0`

> [!WARNING]
>
> **This is an extremely advanced pattern that most users should avoid.** Building a secure OAuth 2.1 server requires deep expertise in authentication protocols, cryptography, and security best practices. The complexity extends far beyond initial implementation to include ongoing security monitoring, threat response, and compliance maintenance.
>
> **Use [Remote OAuth](https://gofastmcp.com/docs/v2/servers/auth/remote-oauth.md) instead** unless you have compelling requirements that external identity providers cannot meet, such as air-gapped environments or specialized compliance needs.

The Full OAuth Server pattern exists to support the MCP protocol specification's requirements. Your FastMCP server becomes both an Authorization Server and Resource Server, handling the complete authentication lifecycle from user login to token validation.

This documentation exists for completeness - the vast majority of applications should use external identity providers instead.

## OAuthProvider

FastMCP provides the `OAuthProvider` abstract class that implements the OAuth 2.1 specification. To use this pattern, you must subclass `OAuthProvider` and implement all required abstract methods.

> [!NOTE]
>
> `OAuthProvider` handles OAuth endpoints, protocol flows, and security requirements, but delegates all storage, user management, and business logic to your implementation of the abstract methods.

## Required Implementation

You must implement these abstract methods to create a functioning OAuth server:

### Client Management

> [card] Client Management Methods
>
> **get\_client** `async method`
>
> Retrieve client information by ID from your database.
>
> **Parameters**
>
> **client\_id** `str`
>
> Client identifier to look up
>
> **Returns**
>
> **OAuthClientInformationFull | None** `return type`
>
> Client information object or `None` if client not found
>
> **register\_client** `async method`
>
> Store new client registration information in your database.
>
> **Parameters**
>
> **client\_info** `OAuthClientInformationFull`
>
> Complete client registration information to store
>
> **Returns**
>
> **None** `return type`
>
> No return value

### Authorization Flow

> [card] Authorization Flow Methods
>
> **authorize** `async method`
>
> Handle authorization request and return redirect URL. Must implement user authentication and consent collection.
>
> **Parameters**
>
> **client** `OAuthClientInformationFull`
>
> OAuth client making the authorization request
>
> **params** `AuthorizationParams`
>
> Authorization request parameters from the client
>
> **Returns**
>
> **str** `return type`
>
> Redirect URL to send the client to
>
> **load\_authorization\_code** `async method`
>
> Load authorization code from storage by code string. Return `None` if code is invalid or expired.
>
> **Parameters**
>
> **client** `OAuthClientInformationFull`
>
> OAuth client attempting to use the authorization code
>
> **authorization\_code** `str`
>
> Authorization code string to look up
>
> **Returns**
>
> **AuthorizationCode | None** `return type`
>
> Authorization code object or `None` if not found

### Token Management

> [card] Token Management Methods
>
> **exchange\_authorization\_code** `async method`
>
> Exchange authorization code for access and refresh tokens. Must validate code and create new tokens.
>
> **Parameters**
>
> **client** `OAuthClientInformationFull`
>
> OAuth client exchanging the authorization code
>
> **authorization\_code** `AuthorizationCode`
>
> Valid authorization code object to exchange
>
> **Returns**
>
> **OAuthToken** `return type`
>
> New OAuth token containing access and refresh tokens
>
> **load\_refresh\_token** `async method`
>
> Load refresh token from storage by token string. Return `None` if token is invalid or expired.
>
> **Parameters**
>
> **client** `OAuthClientInformationFull`
>
> OAuth client attempting to use the refresh token
>
> **refresh\_token** `str`
>
> Refresh token string to look up
>
> **Returns**
>
> **RefreshToken | None** `return type`
>
> Refresh token object or `None` if not found
>
> **exchange\_refresh\_token** `async method`
>
> Exchange refresh token for new access/refresh token pair. Must validate scopes and token.
>
> **Parameters**
>
> **client** `OAuthClientInformationFull`
>
> OAuth client using the refresh token
>
> **refresh\_token** `RefreshToken`
>
> Valid refresh token object to exchange
>
> **scopes** `list[str]`
>
> Requested scopes for the new access token
>
> **Returns**
>
> **OAuthToken** `return type`
>
> New OAuth token with updated access and refresh tokens
>
> **load\_access\_token** `async method`
>
> Load an access token by its token string.
>
> **Parameters**
>
> **token** `str`
>
> The access token to verify
>
> **Returns**
>
> **AccessToken | None** `return type`
>
> The access token object, or `None` if the token is invalid
>
> **revoke\_token** `async method`
>
> Revoke access or refresh token, marking it as invalid in storage.
>
> **Parameters**
>
> **token** `AccessToken | RefreshToken`
>
> Token object to revoke and mark invalid
>
> **Returns**
>
> **None** `return type`
>
> No return value
>
> **verify\_token** `async method`
>
> Verify bearer token for incoming requests. Return `AccessToken` if valid, `None` if invalid.
>
> **Parameters**
>
> **token** `str`
>
> Bearer token string from incoming request
>
> **Returns**
>
> **AccessToken | None** `return type`
>
> Access token object if valid, `None` if invalid or expired

Each method must handle storage, validation, security, and error cases according to the OAuth 2.1 specification. The implementation complexity is substantial and requires expertise in OAuth security considerations.

> [!WARNING]
>
> **Security Notice:** OAuth server implementation involves numerous security considerations including PKCE, state parameters, redirect URI validation, token binding, replay attack prevention, and secure storage requirements. Mistakes can lead to serious security vulnerabilities.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.