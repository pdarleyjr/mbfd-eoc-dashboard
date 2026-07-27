import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {ignores: ['dist', 'coverage', 'playwright-report', 'test-results']},
  {
    extends: [js.configs.recommended, ...tseslint.configs.strictTypeChecked],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      parserOptions: {project: ['./tsconfig.app.json', './tsconfig.node.json']},
    },
    plugins: {'react-hooks': reactHooks, 'react-refresh': reactRefresh},
    rules: {
      ...reactHooks.configs.flat.recommended.rules,
      'react-refresh/only-export-components': ['warn', {allowConstantExport: true}],
      '@typescript-eslint/no-misused-promises': ['error', {checksVoidReturn: {attributes: false}}],
      '@typescript-eslint/no-confusing-void-expression': 'off',
      '@typescript-eslint/no-unnecessary-condition': 'off',
      '@typescript-eslint/restrict-template-expressions': ['error', {allowNumber: true}],
    },
  },
)
