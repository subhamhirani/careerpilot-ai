-- Create api_settings table
CREATE TABLE IF NOT EXISTS api_settings (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    api_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create unique constraint on provider and model_name to prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_settings_provider_model ON api_settings(provider, model_name);

-- Insert default settings if not exists (optional)
INSERT INTO api_settings (provider, model_name, api_key, is_active)
VALUES ('openrouter', 'openai/gpt-4o', '', TRUE)
ON CONFLICT (provider, model_name) DO NOTHING;