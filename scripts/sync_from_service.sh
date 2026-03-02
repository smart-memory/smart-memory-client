#!/bin/bash
# Sync generated client from smart-memory-service repository

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_DIR="${SERVICE_DIR:-../smart-memory-service}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}SmartMemory Client - Sync from Service${NC}"
echo "=========================================="

# Check if service directory exists
if [ ! -d "$SERVICE_DIR" ]; then
    echo -e "${RED}Error: Service directory not found: $SERVICE_DIR${NC}"
    echo "Set SERVICE_DIR environment variable or run from correct location"
    exit 1
fi

echo -e "${YELLOW}Service directory: $SERVICE_DIR${NC}"
echo -e "${YELLOW}Client directory: $CLIENT_DIR${NC}"

# Check if generated code exists in service
if [ ! -d "$SERVICE_DIR/service_common/clients/generated/smart_memory_service_client" ]; then
    echo -e "${RED}Error: Generated client not found in service repo${NC}"
    echo "Run: cd $SERVICE_DIR && ./scripts/generate_client.sh"
    exit 1
fi

# Backup current generated code
if [ -d "$CLIENT_DIR/smartmemory_client/generated" ]; then
    echo -e "${YELLOW}Backing up current generated code...${NC}"
    rm -rf "$CLIENT_DIR/smartmemory_client/generated.backup"
    cp -r "$CLIENT_DIR/smartmemory_client/generated" "$CLIENT_DIR/smartmemory_client/generated.backup"
fi

# Copy generated code
echo -e "${YELLOW}Copying generated code from service...${NC}"
rm -rf "$CLIENT_DIR/smartmemory_client/generated"
mkdir -p "$CLIENT_DIR/smartmemory_client/generated"
cp -r "$SERVICE_DIR/service_common/clients/generated/smart_memory_service_client/"* \
      "$CLIENT_DIR/smartmemory_client/generated/"

# Copy wrapper (optional - only if you want to sync it)
if [ "$SYNC_WRAPPER" = "true" ]; then
    echo -e "${YELLOW}Copying wrapper from service...${NC}"
    cp "$SERVICE_DIR/service_common/clients/smartmemory_client.py" \
       "$CLIENT_DIR/smartmemory_client/client.py"
    
    # Update imports in wrapper
    echo -e "${YELLOW}Updating imports in wrapper...${NC}"
    sed -i '' 's/from service_common\.clients\.generated\.smart_memory_service_client/from smartmemory_client.generated/g' \
        "$CLIENT_DIR/smartmemory_client/client.py"
fi

# Copy OpenAPI schema
if [ -f "$SERVICE_DIR/openapi.schema.json" ]; then
    echo -e "${YELLOW}Copying OpenAPI schema...${NC}"
    cp "$SERVICE_DIR/openapi.schema.json" "$CLIENT_DIR/openapi.schema.json"
fi

# Sync VERSION file from smart-memory-core (source of truth)
SMARTMEMORY_DIR="${SMARTMEMORY_DIR:-$(dirname $(dirname $SERVICE_DIR))/smart-memory}"
if [ -f "$SMARTMEMORY_DIR/VERSION" ]; then
    echo -e "${YELLOW}Syncing VERSION from smart-memory...${NC}"
    cp "$SMARTMEMORY_DIR/VERSION" "$CLIENT_DIR/VERSION"
    
    VERSION=$(cat "$CLIENT_DIR/VERSION" | tr -d '\n\r')
    echo -e "${GREEN}✅ Version synced to: $VERSION${NC}"
    echo -e "${BLUE}ℹ  pyproject.toml reads version dynamically from VERSION file${NC}"
fi

echo -e "${GREEN}✅ Sync complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Test: pytest tests/"
echo "  3. Commit: git add . && git commit -m 'Sync from service'"
echo "  4. Publish: python -m build && twine upload dist/*"
echo ""
echo "Note: Version is automatically read from VERSION file - no manual updates needed!"
