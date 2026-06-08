import React from 'react';
import { Box, Text } from 'src/ink.js';

const DREAMSEED_PRODUCT_NAME = 'DreamSeed Code';
const DREAMSEED_VERSION = '0.1.0';

export function WelcomeV2() {
  return (
    <Box flexDirection="column" paddingX={1} paddingY={1}>
      <Text>
        <Text color="claude">Welcome to {DREAMSEED_PRODUCT_NAME} </Text>
        <Text dimColor={true}>v{DREAMSEED_VERSION}</Text>
      </Text>
    </Box>
  );
}
