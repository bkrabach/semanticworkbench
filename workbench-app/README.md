# Semantic Workbench App Setup Guide

The Semantic Workbench app is a React/Typescript app integrated with the [Semantic Workbench](../workbench-service/README.md) backend service.

Follow the [setup guide](../docs/SETUP_DEV_ENVIRONMENT.md) to install the development tools.

## Installing dependencies

In the [workbench-app](./) directory

```sh
make
```

## Running from VS Code

To run and/or debug in VS Code, View->Run, "app: semantic-workbench-app"

## Running from the command line

In the [workbench-app](./) directory

```sh
pnpm start
```

Note: you might be prompted for admin credentials for the SSL certificates used by the app.

## Extra information

### Scripts

-   `pnpm start` - start dev server
-   `pnpm build` - build for production
-   `pnpm preview` - locally preview production build

### More info

-   [Message Metadata](./docs/MESSAGE_METADATA.md)
-   [Message Types](./docs/MESSAGE_TYPES.md)
-   [State Inspectors](./docs/STATE_INSPECTORS.md)
