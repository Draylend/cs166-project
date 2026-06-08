-- User Indexes
CREATE INDEX idx_users_login ON users(login);
CREATE INDEX idx_users_role ON users(role);

-- Items Indexes
CREATE INDEX idx_item_seller_login ON item(seller_login);
CREATE INDEX idx_item_category ON item(category);
CREATE INDEX idx_item_item_name ON item(item_name);

-- Auction Indexes
CREATE INDEX idx_auction_item_id ON auction(item_id);
CREATE INDEX idx_auction_seller_login ON auction(seller_login);

-- Bid Indexes
CREATE INDEX idx_bid_auction_id_timestamp ON bid(auction_id, bid_timestamp DESC);
CREATE INDEX idx_bid_auction_id_amount ON bid(auction_id, bid_amount DESC);

-- Shipment Indexes
CREATE INDEX idx_shipment_auction_id ON shipment(auction_id);

-- Payment Indexes
CREATE INDEX idx_payment_auction_id ON payment(auction_id);
CREATE INDEX idx_payment_buyer_login ON payment(buyer_login);
