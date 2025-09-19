-- Create product reviews table
CREATE TABLE IF NOT EXISTS product_reviews (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_account TEXT NOT NULL,
    review_text TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure one review per user per product
    UNIQUE(product_id, user_account)
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_product_reviews_product_id ON product_reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_product_reviews_user_account ON product_reviews(user_account);
CREATE INDEX IF NOT EXISTS idx_product_reviews_created_at ON product_reviews(created_at);

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER handle_product_reviews_updated_at
    BEFORE UPDATE ON product_reviews
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

-- Enable RLS (Row Level Security)
ALTER TABLE product_reviews ENABLE ROW LEVEL SECURITY;

-- Add RLS policies
CREATE POLICY "Allow public read access to reviews"
    ON product_reviews FOR SELECT
    USING (true);

CREATE POLICY "Allow users to insert their own reviews"
    ON product_reviews FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Allow users to update their own reviews"
    ON product_reviews FOR UPDATE
    USING (user_account = current_setting('app.current_user_email', true));

CREATE POLICY "Allow users to delete their own reviews"
    ON product_reviews FOR DELETE
    USING (user_account = current_setting('app.current_user_email', true));