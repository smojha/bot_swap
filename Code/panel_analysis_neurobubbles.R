# Install packages
install.packages("openxlsx")
install.packages("zoo")
install.packages("car")
install.packages("forecast")
install.packages("FinTS")
install.packages("urca")
install.packages("CADFtest")
install.packages("nlme")


#Load libraries
library(nlme)
library(CADFtest)
library(readr)
library(dplyr)
library(ggplot2)
library(lme4) # for mixed-effects models
library(readxl)
library(tidyr)
library(openxlsx)
library(zoo)
library(reshape2)
library(gridExtra) # For arranging the two plots
library(plm)
library(lmtest)
library(sandwich)
library(forecast)
library(FinTS)
library(urca)
library(writexl)

rm(list=ls())

# Load the data
# Rounds
data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/data_panel_4markets.xlsx', sheet='Panel rounds') # Rounds panel data from 2 hybrid markets

# Orders
data_orders <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/data_panel_4markets.xlsx', sheet='Panel orders') # Orders panel data from 2 hybrid markets

data_orders <- data_orders %>%
  rename(period = round_number)
data <- data %>%
  rename(period = subsession.round_number)

## Import EDA data
eda_tonic_panel <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/EDA_panel_June6.xlsx', sheet = 'Tonic Order-submission') # eda_panel_updated3
eda_phasic_panel <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/EDA_panel_June6.xlsx', sheet = 'Phasic Order-submission') # eda_panel_updated3

# Rename the 'Mean' column in each dataframe for clarity
eda_tonic_panel <- eda_tonic_panel %>%
  rename(participant.label = 'subject_id') #EDA_tonic_mean = Mean, 

eda_phasic_panel <- eda_phasic_panel %>%
  rename(participant.label = 'subject_id') #EDA_phasic_mean = Mean, 


## Drop first 3 periods (training rounds)
# Remove periods 1-3 from each market and renumber periods from 1-30
data <- data %>%
  filter(period > 3) %>%
  group_by(market_id) %>%
  mutate(period = period - 3) %>%
  ungroup()

# Filter out the training rounds and renumber periods 4-33 to 1-30 in data_orders
data_orders <- data_orders %>%
  filter(period > 3) %>%
  mutate(period = period - 3)

# Sort by participant and period 
data <- data %>%
  arrange(market_id, participant.id_in_session, period) %>%
  group_by(market_id, participant.id_in_session) %>%
  mutate(
    dose_r_ma3 = rollmean(player.dose_r, 3, fill = NA, align = 'right'),
    dose_r_ma5 = rollmean(player.dose_r, 5, fill = NA, align = 'right'),
    dose_mu_ma3 = rollmean(player.dose_mu, 3, fill = NA, align = 'right'),
    dose_mu_ma5 = rollmean(player.dose_mu, 5, fill = NA, align = 'right'),
    log_returns_lead5 = dplyr::lead(log_returns, 5)  # Assuming 'log_returns' column exists and is numeric
  )

# Data forecast
# Function to shift forecast columns forward with NA padding
shift_forecast <- function(forecast, shift) {
  c(rep(NA, shift), forecast)[1:length(forecast)]
}

# Applying the function to each forecast column within the data frame and create a new data structure data_forecast.
data_forecast <- data %>%
  group_by(market_id, participant.label) %>%
  mutate(
    forecast_f0 = player.f0,  # No shift needed
    forecast_f1 = shift_forecast(player.f1, 2),  # Shift 2 periods forward
    forecast_f2 = shift_forecast(player.f2, 5),  # Shift 5 periods forward
    forecast_f3 = shift_forecast(player.f3, 10),  # Shift 10 periods forward
    group_price = group.price,  # Include market price
    group_volume = group.volume  # Include market volume
  ) %>%
  ungroup() %>%
  # Select and arrange the desired columns
  select(participant.label, market_id, period, group_price, group_volume, forecast_f0, forecast_f1, forecast_f2, forecast_f3, log_returns) %>%
  arrange(market_id, participant.label, period)  # Ensure data is sorted


# Calculate the deviations of forecasts from the market price for each participant in each market
data_forecast <- data_forecast %>%
  group_by(market_id, participant.label) %>%
  mutate(
    deviation_f0 = group_price - forecast_f0,
    deviation_f1 = group_price - forecast_f1,
    deviation_f2 = group_price - forecast_f2,
    deviation_f3 = group_price - forecast_f3,
    pct_change_deviation_f0 = ifelse(forecast_f0 != 0, (deviation_f0 / forecast_f0) * 100, NA_real_),
    pct_change_deviation_f1 = ifelse(forecast_f1 != 0, (deviation_f1 / forecast_f1) * 100, NA_real_),
    pct_change_deviation_f2 = ifelse(forecast_f2 != 0, (deviation_f2 / forecast_f2) * 100, NA_real_),
    pct_change_deviation_f3 = ifelse(forecast_f3 != 0, (deviation_f3 / forecast_f3) * 100, NA_real_)
    
  ) %>%
  ungroup() %>%
  arrange(market_id, participant.label, period)  # Ensuring final sort order after all transformations

## Merge EDA with data for regression analysis
# Intermediary: need to fix this: Remove the prefix "vbm55dq7_" from participant.label in the data for market 4
data$participant.label <- sub("^vbm55dq7_", "", data$participant.label)

# Step 1: Create lists of unique participants in EDA data
participants_tonic <- unique(eda_tonic_panel$participant.label)
participants_phasic <- unique(eda_phasic_panel$participant.label)

# Step 2: Filter data for participants found in both EDA datasets
common_participants <- intersect(participants_tonic, participants_phasic)
common_participants <- common_participants[!is.na(common_participants)]

# Filter the main dataset based on this common participant list
data_filtered <- data %>%
  filter(participant.label %in% common_participants)

# Step 3: Merge EDA data with filtered data
# Note: Ensure that the EDA data frames have columns named consistently with data_filtered for a successful merge
data_eda <- data_filtered %>%
  left_join(eda_tonic_panel, by = c("market_id", "period", "participant.label")) %>%
  left_join(eda_phasic_panel, by = c("market_id", "period", "participant.label"))

# Step 4: 
#### Analysis section
# 4.1.  Market prices
# Extract unique market prices for each period in each market, selecting only the needed columns
market_prices <- data %>%
  select(market_id, period, group.price) %>%  # Select only the columns of interest
  distinct(market_id, period, group.price) %>%
  arrange(market_id, period)  # Organize data by market and period for easier readability

# 4.2. Extract unique market volumes for each period in each market, selecting only the needed columns
market_volumes <- data %>%
  select(market_id, period, group.volume) %>%  # Select only the columns of interest
  distinct(market_id, period, group.volume) %>%
  arrange(market_id, period)  # Organize data by market and period for easier readability

# 4.3. Calculate standard error of volume per period across markets
market_volumes_se <- market_volumes %>%
  group_by(period) %>%
  summarise(
    average_volume = mean(group.volume, na.rm = TRUE),
    se_volume = sd(group.volume, na.rm = TRUE) / sqrt(n())
  ) %>%
  ungroup()

# Separate the average prices for each market for plotting
avg_price_market1 <- market_prices %>% filter(market_id == 1)
avg_price_market2 <- market_prices %>% filter(market_id == 2)
avg_price_market3 <- market_prices %>% filter(market_id == 3)
avg_price_market4 <- market_prices %>% filter(market_id == 4)

# Calculate the overall average price across markets for each period
overall_avg_price <- data %>%
  group_by(period) %>%
  summarise(overall_average_price = mean(group.price, na.rm = TRUE)) %>%
  ungroup()

# 4.4 Price dynamics plot with corrected legend colors and increased text size
p1 <- ggplot() +
  geom_line(data = avg_price_market1, aes(x = period, y = group.price, color = "Hybrid March 7th"), size = 1.2) +
  geom_point(data = avg_price_market1, aes(x = period, y = group.price, color = "Hybrid March 7th"), size = 3) +
  geom_line(data = avg_price_market2, aes(x = period, y = group.price, color = "Hybrid March 14th"), size = 1.2) +
  geom_point(data = avg_price_market2, aes(x = period, y = group.price, color = "Hybrid March 14th"), size = 3) +
  geom_line(data = avg_price_market3, aes(x = period, y = group.price, color = "Hybrid April 4th"), size = 1.2) +
  geom_point(data = avg_price_market3, aes(x = period, y = group.price, color = "Hybrid April 4th"), size = 3) +
  geom_line(data = avg_price_market4, aes(x = period, y = group.price, color = "Hybrid June 6th"), size = 1.2) +
  geom_point(data = avg_price_market4, aes(x = period, y = group.price, color = "Hybrid June 6th"), size = 3) +
  geom_line(data = overall_avg_price, aes(x = period, y = overall_average_price, color = "Average across Markets"), size = 1.5) +
  geom_point(data = overall_avg_price, aes(x = period, y = overall_average_price, color = "Average across Markets"), size = 3) +
  scale_color_manual(values = c("Hybrid March 7th" = "blue", 
                                "Hybrid March 14th" = "red", 
                                "Hybrid April 4th" = "green",
                                "Hybrid June 6th" = "purple",
                                "Average across Markets" = "black")) +
  labs(title = "Price Dynamics", x = "Period", y = "Price", color = "Market") +
  theme_minimal() +
  theme(text = element_text(size = 16), legend.position = "bottom", legend.title = element_text(size = 14), legend.text = element_text(size = 12))

plot(p1)

# Volume plot with standard error bars, adjusted legend for volume
p2 <- ggplot(market_volumes_se, aes(x = period, y = average_volume, fill = "Volume")) +
  geom_bar(stat = "identity") +
  geom_errorbar(aes(ymin = average_volume - se_volume, ymax = average_volume + se_volume), width = 0.2, color = "black") +
  scale_fill_manual(values = "blue", labels = "Average Volume") +
  labs(title = "Volume with Standard Error", x = "Period", y = "Volume", fill = "Legend") +
  theme_minimal() +
  theme(text = element_text(size = 16), legend.position = "bottom", legend.title = element_text(size = 14), legend.text = element_text(size = 12))

# 4.4 Final plot --> Arrange the plots one above the other with enhanced legibility
grid.arrange(p1, p2, ncol = 1)

# Saving the combined plot to a file
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/price_volume_plot_panel.png", arrangeGrob(p1, p2), width = 12, height = 10, dpi = 300)

# 4.5 Calculate average bid and ask prices per period

market_prices_1 <- data %>%
  filter(market_id == 1) %>%
  select(period, market_price = group.price) %>%
  distinct()

market_prices_2 <- data %>%
  filter(market_id == 2) %>%
  select(period, market_price = group.price) %>%
  distinct()

market_prices_3 <- data %>%
  filter(market_id == 3) %>%
  select(period, market_price = group.price) %>%
  distinct()

market_prices_4 <- data %>%
  filter(market_id == 4) %>%
  select(period, market_price = group.price) %>%
  distinct()

# Calculate bid and ask prices separately for each market
bid_ask_spread_market1 <- data_orders %>%
  filter(market_id == 1) %>%
  group_by(period) %>%
  summarise(
    min_bid = min(price[type == 'BUY'], na.rm = TRUE),
    max_ask = max(price[type == 'SELL'], na.rm = TRUE)
  ) %>%
  ungroup() %>%
  left_join(market_prices_1, by = "period")  # Joining market price for plotting

bid_ask_spread_market2 <- data_orders %>%
  filter(market_id == 2) %>%
  group_by(period) %>%
  summarise(
    min_bid = min(price[type == 'BUY'], na.rm = TRUE),
    max_ask = max(price[type == 'SELL'], na.rm = TRUE)
  ) %>%
  ungroup() %>%
  left_join(market_prices_2, by = "period")  # Joining market price for plotting


bid_ask_spread_market3 <- data_orders %>%
  filter(market_id == 3) %>%
  group_by(period) %>%
  summarise(
    min_bid = min(price[type == 'BUY'], na.rm = TRUE),
    max_ask = max(price[type == 'SELL'], na.rm = TRUE)
  ) %>%
  ungroup() %>%
  left_join(market_prices_3, by = "period")  # Joining market price for plotting


bid_ask_spread_market4 <- data_orders %>%
  filter(market_id == 4) %>%
  group_by(period) %>%
  summarise(
    min_bid = min(price[type == 'BUY'], na.rm = TRUE),
    max_ask = max(price[type == 'SELL'], na.rm = TRUE)
  ) %>%
  ungroup() %>%
  left_join(market_prices_4, by = "period")  # Joining market price for plotting


# Create a plot for the bid-ask spread of market 1
p_bid_ask_m1 <- ggplot(data = bid_ask_spread_market1, aes(x = period)) +
  geom_linerange(aes(ymin = min_bid, ymax = max_ask), color = "red", size = 0.5) +
  geom_point(aes(y = market_price), color = "blue", size = 2, shape = 20) +  # Use market_price for points
  geom_line(aes(y = market_price), color = "blue", size = 1) +  # Use market_price for line
  labs(title = "Bid-Ask Spread and Market Price for Market 1", x = "Period", y = "Price") +
  theme_minimal()

p_bid_ask_m1

# Add market price line to the bid-ask spread plot for Market 2
p_bid_ask_m2 <- ggplot(data = bid_ask_spread_market2, aes(x = period)) +
  geom_linerange(aes(ymin = min_bid, ymax = max_ask), color = "red", size = 0.5) +
  geom_point(aes(y = market_price), color = "blue", size = 2, shape = 20) +  # Circle for market price
  geom_line(aes(y = market_price), color = "blue", size = 1) +
  labs(title = "Bid-Ask Spread and Market Price for Market 2", x = "Period", y = "Price") +
  theme_minimal()

p_bid_ask_m2

# Add market price line to the bid-ask spread plot for Market 3
p_bid_ask_m3 <- ggplot(data = bid_ask_spread_market3, aes(x = period)) +
  geom_linerange(aes(ymin = min_bid, ymax = max_ask), color = "red", size = 0.5) +
  geom_point(aes(y = market_price), color = "blue", size = 2, shape = 20) +  # Circle for market price
  geom_line(aes(y = market_price), color = "blue", size = 1) +
  labs(title = "Bid-Ask Spread and Market Price for Market 3", x = "Period", y = "Price") +
  theme_minimal()

p_bid_ask_m3

# Add market price line to the bid-ask spread plot for Market 3
p_bid_ask_m4 <- ggplot(data = bid_ask_spread_market4, aes(x = period)) +
  geom_linerange(aes(ymin = min_bid, ymax = max_ask), color = "red", size = 0.5) +
  geom_point(aes(y = market_price), color = "blue", size = 2, shape = 20) +  # Circle for market price
  geom_line(aes(y = market_price), color = "blue", size = 1) +
  labs(title = "Bid-Ask Spread and Market Price for Market 4", x = "Period", y = "Price") +
  theme_minimal()

p_bid_ask_m4


# Combine both bid-ask spread plots using gridExtra
bid_ask_graph = grid.arrange(p_bid_ask_m1, p_bid_ask_m2, p_bid_ask_m3, p_bid_ask_m4, nrow=2, ncol = 2)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/bid_ask_spread_4markets.png", bid_ask_graph, width = 12, height = 10, dpi = 300)


# 4.6 Add several variables to calculate other indicators
# First, separate the bids and asks into two dataframes
bids <- data_orders %>% filter(type == "BUY")
asks <- data_orders %>% filter(type == "SELL")

# Calculate BestBid and BidAmount
best_bids <- bids %>%
  group_by(market_id, period) %>%
  summarise(BestBid = max(price, na.rm = TRUE),
            BidAmount = first(quantity[price == BestBid])) %>%
  ungroup()

# Calculate BestAsk and AskAmount
best_asks <- asks %>%
  group_by(market_id, period) %>%
  summarise(BestAsk = min(price, na.rm = TRUE),
            AskAmount = first(quantity[price == BestAsk])) %>%
  ungroup()

# Merge the best_bids and best_asks back to data_orders
# This step assumes that every period in data_orders should have both a bid and an ask;
# If not, adjustments may be needed
data_orders <- data_orders %>%
  left_join(best_bids, by = c("market_id", "period")) %>%
  left_join(best_asks, by = c("market_id", "period"))



# 5. Deviation of forecasts from market prices
# Calculate average volume per period for each market
average_volume_per_market <- data_forecast %>%
  group_by(market_id, period) %>%
  summarise(average_volume = mean(group_volume, na.rm = TRUE)) %>%
  ungroup()

# Prepare a separate dataframe for plotting deviations
deviation_data <- data_forecast %>%
  gather(key = "forecast_type", value = "deviation_value", starts_with("deviation_f"), -market_id, -period, -group_volume)

# Separate dataframe for volume data to align with deviation data structure for faceting
volume_data <- data_forecast %>%
  select(market_id, period, group_volume) %>%
  distinct()

# Calculate average forecasts for each period for each market
avg_forecasts <- data_forecast %>%
  group_by(market_id, period) %>%
  summarise(
    avg_f0 = mean(forecast_f0, na.rm = TRUE),
    avg_f1 = mean(forecast_f1, na.rm = TRUE),
    avg_f2 = mean(forecast_f2, na.rm = TRUE),
    avg_f3 = mean(forecast_f3, na.rm = TRUE),
    market_price = mean(group_price, na.rm = TRUE)  # Ensure there's one price per period per market
  ) %>%
  ungroup()

# Plot for Market 1 with forecasts and market price
plot_market1 <- ggplot(data = filter(avg_forecasts, market_id == 1), aes(x = period)) +
  geom_line(aes(y = avg_f0, color = "Forecast 0 periods ahead (current round)"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f1, color = "Forecast 2 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f2, color = "Forecast 5 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f3, color = "Forecast 10 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = market_price, color = "Market Price"), linetype = "solid", size = 1.2) +
  scale_color_manual(values = c("Forecast 0 periods ahead (current round)" = "blue",
                                "Forecast 2 periods ahead" = "red",
                                "Forecast 5 periods ahead" = "green",
                                "Forecast 10 periods ahead" = "purple",
                                "Market Price" = "black")) +
  labs(title = "Forecasts and Market Price for Market 1", x = "Period", y = "Price/Forecast", color = NULL) +
  theme_minimal() +
  theme(legend.position = "bottom", legend.title = element_blank()) +
  guides(color = guide_legend(nrow = 2, byrow = TRUE))

# Plot for Market 2 with forecasts and market price
plot_market2 <- ggplot(data = filter(avg_forecasts, market_id == 2), aes(x = period)) +
  geom_line(aes(y = avg_f0, color = "Forecast 0 periods ahead (current round)"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f1, color = "Forecast 2 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f2, color = "Forecast 5 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f3, color = "Forecast 10 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = market_price, color = "Market Price"), linetype = "solid", size = 1.2) +
  scale_color_manual(values = c("Forecast 0 periods ahead (current round)" = "blue",
                                "Forecast 2 periods ahead" = "red",
                                "Forecast 5 periods ahead" = "green",
                                "Forecast 10 periods ahead" = "purple",
                                "Market Price" = "black")) +
  labs(title = "Forecasts and Market Price for Market 2", x = "Period", y = "Price/Forecast", color = NULL) +
  theme_minimal() +
  theme(legend.position = "bottom", legend.title = element_blank()) +
  guides(color = guide_legend(nrow = 2, byrow = TRUE))

# Plot for Market 3 with forecasts and market price
plot_market3 <- ggplot(data = filter(avg_forecasts, market_id == 3), aes(x = period)) +
  geom_line(aes(y = avg_f0, color = "Forecast 0 periods ahead (current round)"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f1, color = "Forecast 2 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f2, color = "Forecast 5 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f3, color = "Forecast 10 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = market_price, color = "Market Price"), linetype = "solid", size = 1.2) +
  scale_color_manual(values = c("Forecast 0 periods ahead (current round)" = "blue",
                                "Forecast 2 periods ahead" = "red",
                                "Forecast 5 periods ahead" = "green",
                                "Forecast 10 periods ahead" = "purple",
                                "Market Price" = "black")) +
  labs(title = "Forecasts and Market Price for Market 3", x = "Period", y = "Price/Forecast", color = NULL) +
  theme_minimal() +
  theme(legend.position = "bottom", legend.title = element_blank()) +
  guides(color = guide_legend(nrow = 2, byrow = TRUE))

# Plot for Market 4 with forecasts and market price
plot_market4 <- ggplot(data = filter(avg_forecasts, market_id == 4), aes(x = period)) +
  geom_line(aes(y = avg_f0, color = "Forecast 0 periods ahead (current round)"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f1, color = "Forecast 2 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f2, color = "Forecast 5 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = avg_f3, color = "Forecast 10 periods ahead"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = market_price, color = "Market Price"), linetype = "solid", size = 1.2) +
  scale_color_manual(values = c("Forecast 0 periods ahead (current round)" = "blue",
                                "Forecast 2 periods ahead" = "red",
                                "Forecast 5 periods ahead" = "green",
                                "Forecast 10 periods ahead" = "purple",
                                "Market Price" = "black")) +
  labs(title = "Forecasts and Market Price for Market 4", x = "Period", y = "Price/Forecast", color = NULL) +
  theme_minimal() +
  theme(legend.position = "bottom", legend.title = element_blank()) +
  guides(color = guide_legend(nrow = 2, byrow = TRUE))



# Display the plots
plot_market1 # still need to shift observations
plot_market2
plot_market3
plot_market4


# Combine both bid-ask spread plots using gridExtra
forecasts_4markets = grid.arrange(plot_market1, plot_market2, plot_market3, plot_market4, nrow=2, ncol = 2)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/forecasts_4markets.png", forecasts_4markets, width = 14, height = 10, dpi = 300)


# 6. Add variables
data_orders <- data_orders %>%
  mutate(
    # Calculate Net Order Book Pressure
    NetOrderBookPressure = (BestBid * BidAmount + BestAsk * AskAmount) / (BidAmount + AskAmount),
  )

data <- data %>%
  mutate(
    CashValue = player.cash,
    StockValue = player.shares * group.price,
    # Calculate Cash Value to Stock Value Ratio, handle division by zero
    CashValue_StockValue_ratio = ifelse(StockValue == 0, NA, CashValue / StockValue)
  )



#### Multiple regression - panel data #####
# Step 1. Aggregate data properly and make sure deviations_f[x] exist in data

data <- data %>%
  mutate(entity_id = paste(market_id, participant.label, sep = "_"))

data_forecast <- data_forecast %>%
  mutate(entity_id = paste(market_id, participant.label, sep = "_"))

# Prepare the subset of data_forecast with required columns for merging
forecast_columns <- c("entity_id", "period", "deviation_f0", "deviation_f1", "deviation_f2", "deviation_f3", 
                      "pct_change_deviation_f0", "pct_change_deviation_f1", "pct_change_deviation_f2", "pct_change_deviation_f3")
data_forecast_sub <- data_forecast[forecast_columns]

# Ensure data_eda has the same entity_id identifier for merging
data_eda <- data_eda %>%
  mutate(entity_id = paste(market_id, participant.label, sep = "_"))

eda_columns <- c("entity_id", "period", "Mean.x", "Delta_Mean.x", "EDA_ma3.x", "Delta_EDA_ma3.x", "Delta_percent_EDA_ma3.x", "EDA_ma5.x", "Delta_EDA_ma5.x", "Delta_percent_EDA_ma5.x", "Delta_percent_Mean.x", "Peak Count.x")
data_eda_sub <- data_eda[eda_columns]

# Merge data and data_forecast_sub first to create data_all
data_all <- merge(data, data_forecast_sub, by = c("entity_id", "period"), all.x = TRUE)

# Merge data using the entity_id and period as keys
data_all <- merge(data_all, data_eda_sub, by = c("entity_id", "period"), all.x = TRUE)

output_file <- "/Users/mihai/PycharmProjects/stockPredict/neurofinance/results/merged_data_only_eda.xlsx"
write_xlsx(data_all, path = output_file)

# Check the first few rows of the merged data to ensure accuracy
head(data_all)

# Step 2. Test ADF 
data_all <- data_all %>%
  group_by(market_id, participant.label) %>%
  mutate(
    forecast_f0 = player.f0,  # No shift needed
    forecast_f1 = shift_forecast(player.f1, 2),  # Shift 2 periods forward
    forecast_f2 = shift_forecast(player.f2, 5),  # Shift 5 periods forward
    forecast_f3 = shift_forecast(player.f3, 10)  # Shift 10 periods forward
  ) %>%
  ungroup()

data_agg <- data_all %>%
  group_by(market_id, period) %>%
  summarise(
    avg_log_returns = mean(log_returns, na.rm = TRUE),
    avg_price = mean(group.price, na.rm = TRUE),
    avg_Mean_eda = mean(Mean.x, na.rm = TRUE),
    avg_Delta_Mean_eda = mean(Delta_Mean.x, na.rm = TRUE),
    avg_Delta_percent_Mean_eda = mean(Delta_percent_Mean.x, na.rm = TRUE),
    avg_Mean_eda_ma3 = mean(EDA_ma3.x, na.rm = TRUE),
    avg_Delta_Mean_eda_ma3 = mean(Delta_EDA_ma3.x, na.rm = TRUE),
    avg_Delta_percent_Mean_eda_ma3 = mean(Delta_percent_EDA_ma3.x, na.rm = TRUE),
    avg_Mean_eda_ma5 = mean(EDA_ma5.x, na.rm = TRUE),
    avg_Delta_Mean_eda_ma5 = mean(Delta_EDA_ma5.x, na.rm = TRUE),
    avg_Delta_percent_Mean_eda_ma5 = mean(Delta_percent_EDA_ma5.x, na.rm = TRUE),
    avg_forecast_f0 = mean(forecast_f0, na.rm = TRUE),
    avg_forecast_f1 = mean(forecast_f1, na.rm = TRUE),
    avg_forecast_f2 = mean(forecast_f2, na.rm = TRUE),
    avg_forecast_f3 = mean(forecast_f3, na.rm = TRUE),
    avg_deviation_f0 = mean(group.price - forecast_f0, na.rm = TRUE),
    avg_deviation_f1 = mean(group.price - forecast_f1, na.rm = TRUE),
    avg_deviation_f2 = mean(group.price - forecast_f2, na.rm = TRUE),
    avg_deviation_f3 = mean(group.price - forecast_f3, na.rm = TRUE)
  ) %>%
  ungroup()

# Function to apply ADF test and return the p-value
library(tseries)

# Corrected function to apply ADF test and return the p-value
apply_adf_test_with_na_replacement <- function(series) {
  if (sum(!is.na(series)) > 3) {  # Check if there are at least 4 non-NA data points
    # Replace NAs with the mean of the available data
    series[is.na(series)] <- mean(series, na.rm = TRUE)
    adf_test_result <- adf.test(series, k = 3)$p.value
  } else {
    adf_test_result <- NA  # Return NA if there aren't enough data points even after NA replacement
  }
  return(adf_test_result)
}



# Applying ADF test to each variable
adf_results <- data_agg %>%
  summarise(
    p_value_log_returns = apply_adf_test_with_na_replacement(avg_log_returns),
    p_value_price = apply_adf_test_with_na_replacement(avg_price),
    p_value_Mean_eda = apply_adf_test_with_na_replacement(avg_Mean_eda),
    p_value_Delta_Mean_eda = apply_adf_test_with_na_replacement(avg_Delta_Mean_eda),
    p_value_Delta_percent_Mean_eda = apply_adf_test_with_na_replacement(avg_Delta_percent_Mean_eda),
    p_value_Mean_eda_ma3 = apply_adf_test_with_na_replacement(avg_Mean_eda_ma3),
    p_value_Delta_Mean_eda_ma3 = apply_adf_test_with_na_replacement(avg_Delta_Mean_eda_ma3),
    p_value_Delta_percent_Mean_eda_ma3 = apply_adf_test_with_na_replacement(avg_Delta_percent_Mean_eda_ma3),
    p_value_Mean_eda_ma5 = apply_adf_test_with_na_replacement(avg_Mean_eda_ma5),
    p_value_Delta_Mean_eda_ma5 = apply_adf_test_with_na_replacement(avg_Delta_Mean_eda_ma5),
    p_value_Delta_percent_Mean_eda_ma5 = apply_adf_test_with_na_replacement(avg_Delta_percent_Mean_eda_ma5),
    p_value_forecast_f0 = apply_adf_test_with_na_replacement(avg_forecast_f0),
    p_value_forecast_f1 = apply_adf_test_with_na_replacement(avg_forecast_f1),
    p_value_forecast_f2 = apply_adf_test_with_na_replacement(avg_forecast_f2),
    p_value_forecast_f3 = apply_adf_test_with_na_replacement(avg_forecast_f3),
    p_value_deviation_f0 = apply_adf_test_with_na_replacement(avg_deviation_f0),
    p_value_deviation_f1 = apply_adf_test_with_na_replacement(avg_deviation_f1),
    p_value_deviation_f2 = apply_adf_test_with_na_replacement(avg_deviation_f2),
    p_value_deviation_f3 = apply_adf_test_with_na_replacement(avg_deviation_f3)
  )

# View the results
print(adf_results)

# Step 3. Apply average regression using aggregate data
# Apply shifting in the detailed data, not aggregated
data_eda <- data_eda %>%
  group_by(market_id, participant.label) %>%
  mutate(
    forecast_f0 = player.f0,  # No shift needed
    forecast_f1 = shift_forecast(player.f1, 2),  # Shift 2 periods forward
    forecast_f2 = shift_forecast(player.f2, 5),  # Shift 5 periods forward
    forecast_f3 = shift_forecast(player.f3, 10)  # Shift 10 periods forward
  ) %>%
  ungroup()

# Only use data with participants that wore the E4 empatica 
data_agg_eda <- data_eda %>%
  group_by(market_id, period) %>%
  summarise(
    avg_log_returns = mean(log_returns, na.rm = TRUE),
    avg_price = mean(group.price, na.rm = TRUE),
    avg_volume = mean(group.volume),
    avg_CashStockValueRatio = mean(CashValue_StockValue_ratio),
    avg_Mean_eda = mean(Mean.x, na.rm = TRUE),
    avg_Delta_Mean_eda = mean(Delta_Mean.x, na.rm = TRUE),
    avg_Delta_percent_Mean_eda = mean(Delta_percent_Mean.x, na.rm = TRUE),
    avg_Mean_eda_ma3 = mean(EDA_ma3.x, na.rm = TRUE),
    avg_Delta_Mean_eda_ma3 = mean(Delta_EDA_ma3.x, na.rm = TRUE),
    avg_Delta_percent_Mean_eda_ma3 = mean(Delta_percent_EDA_ma3.x, na.rm = TRUE),
    avg_Mean_eda_ma5 = mean(EDA_ma5.x, na.rm = TRUE),
    avg_Delta_Mean_eda_ma5 = mean(Delta_EDA_ma5.x, na.rm = TRUE),
    avg_Delta_percent_Mean_eda_ma5 = mean(Delta_percent_EDA_ma5.x, na.rm = TRUE),
    avg_forecast_f0 = mean(forecast_f0, na.rm = TRUE),
    avg_forecast_f1 = mean(forecast_f1, na.rm = TRUE),
    avg_forecast_f2 = mean(forecast_f2, na.rm = TRUE),
    avg_forecast_f3 = mean(forecast_f3, na.rm = TRUE),
    avg_deviation_f0 = mean(group.price - forecast_f0, na.rm = TRUE),
    avg_deviation_f1 = mean(group.price - forecast_f1, na.rm = TRUE),
    avg_deviation_f2 = mean(group.price - forecast_f2, na.rm = TRUE),
    avg_deviation_f3 = mean(group.price - forecast_f3, na.rm = TRUE),
    avg_dose_r=mean(player.dose_r),
    avg_dose_mu=mean(player.dose_mu),
    avg_dose_r_ma3=mean(dose_r_ma3),
    avg_dose_r_ma5=mean(dose_r_ma5),
    avg_dose_mu_ma3=mean(dose_mu_ma3),
    avg_dose_mu_ma5=mean(dose_mu_ma5)
  ) %>%
  ungroup()


# Run the regression
regression_result <- lm(avg_log_returns ~ avg_Delta_Mean_eda_ma3 + avg_deviation_f0 + avg_dose_r_ma3 + avg_volume, data = data_agg_eda)
# Display the summary of the regression to see coefficients and statistics
summary(regression_result)
# Control for serial correlation
coeftest(regression_result, vcov = vcovHC(regression_result, type = "HC3"))


# Check for autocorrelation using the Durbin-Watson test
library(lmtest)
dw_test <- durbinWatsonTest(regression_result)
print(dw_test)

# Check for higher order autocorrelation using the Breusch-Godfrey test
bg_test <- bgtest(regression_result, order = 4)  # Checking for up to 4 lags
print(bg_test)

# Check for autocorrelation using the Ljung-Box test on residuals
library(forecast)
lb_test <- Box.test(residuals(regression_result), lag = 10, type = "Ljung-Box")
print(lb_test)

# Check for heteroskedasticity using the Breusch-Pagan test
bp_test <- bptest(regression_result)
print(bp_test)


##### FINAL NON-PANEL MODEL
robust_se <- NeweyWest(regression_result, lag = NULL, prewhite = FALSE, adjust = TRUE)

# Use coeftest to display the summary with Newey-West standard errors
coeftest(regression_result, vcov = robust_se)




# Step 4. Convert your data frame to a pdata.frame, specifying 'market_id' and 'participant.label' as indexes
pdata <- pdata.frame(data_eda, index = c("entity_id", "period"))
check <- table(index(pdata), useNA = "ifany") # ensure only unique ids for panel analysis
View(check) #Freq needs to be 1

pdata <- pdata %>%
  group_by(market_id, participant.label) %>%
  mutate(
    forecast_f0 = player.f0,  # No shift needed
    forecast_f1 = shift_forecast(player.f1, 2),  # Shift 2 periods forward
    forecast_f2 = shift_forecast(player.f2, 5),  # Shift 5 periods forward
    forecast_f3 = shift_forecast(player.f3, 10)  # Shift 10 periods forward
  ) %>%
  ungroup()

pdata <- pdata %>%
  group_by(market_id, participant.label) %>%
  mutate(
    deviation_f0 = group.price - forecast_f0,  # No shift needed
    deviation_f1 = group.price - forecast_f1,  # Shift 2 periods forward
    deviation_f2 = group.price - forecast_f2,  # Shift 5 periods forward
    deviation_f3 = group.price - forecast_f3 # Shift 10 periods forward
  ) %>%
  ungroup()

#Convert pdata to dataframe again
pdata <- pdata.frame(pdata, index = c("entity_id", "period"))

duplicates_check <- data_eda %>%
  group_by(entity_id, period) %>%
  summarise(n = n()) %>%
  filter(n > 1)

# View the results to identify where duplicates are occurring
print(duplicates_check) # Should be 0

# Save file with data before further manipulation and regression analysis 
output_file <- "/Users/mihai/PycharmProjects/stockPredict/neurofinance/results/merged_data_4markets.xlsx"
write_xlsx(pdata, path = output_file)

# Step 3. Linear regression using plm for fixed effects
# Fit a fixed effects model with the data
fe_model <- plm(log_returns ~ Delta_EDA_ma3.x + deviation_f0 + dose_r_ma3 + group.volume,
                    data = pdata, 
                    model = "within")
summary(fe_model)
coeftest(fe_model, vcov = vcovHC(fe_model, method = "arellano", type = "HC1"))

# Fit a random effects model
# Random effects model
re_model <- plm(log_returns ~ Delta_EDA_ma3.x + deviation_f0 + dose_r_ma3 + group.volume,
                            data = pdata, 
                            model = "random")

summary(re_model)
coeftest(re_model, vcov = vcovHC(re_model, method = "arellano", type = "HC1"))


# Performing Breusch-Pagan test from lmtest package
bp_test <- bptest(fe_model)
print(bp_test)

# Durbin-Watson test for autocorrelation, using plm's pbgtest for panels
dw_test <- pbgtest(fe_model, type = "Chisq")
print(dw_test)

# Multicollinearity diagnostics - Not directly applicable in 'plm' with fixed effects,
# but you can run on the model without fixed effects as a reference
library(car)
vif_model <- lm(log_returns ~ lag(log_returns, 1) + Delta_EDA_ma3.x + deviation_f0 + dose_r_ma3 + group.volume, data = pdata)
vif(vif_model)

######## Check endogeneity #######
# Perform the Hausman test
hausman_test <- phtest(fe_model, re_model)
print(hausman_test) # If the test suggests significant differences (p-value < 0.05), it indicates potential endogeneity, justifying the use of GMM and the careful selection of instruments.

## GMM estimation
### Fit a GMM model with instruments
gmm_model <- pgmm(log_returns ~ Delta_EDA_ma3.x + deviation_f0 + dose_r_ma3  | 
                    lag(log_returns, 2:3) + lag(dose_r_ma3, 1:2) + lag(deviation_f0, 1:2),
                  data = pdata, effect = "individual", model = "twosteps")

summary(gmm_model, diagnostics=TRUE)

# Manually create lags

duplicated_rows <- pdata %>%
  group_by(entity_id, period) %>%
  summarize(count = n(), .groups = 'drop') %>%
  filter(count > 1)

# View the results to identify duplicates
print(duplicated_rows)


pdata <- pdata %>%
  group_by(entity_id) %>%
  arrange(period) %>%
  mutate(
    lag_Delta_EDA_ma3_x = lag(Delta_EDA_ma3.x, 1),
    lag_deviation_f0 = lag(deviation_f0, 1),
    lag_dose_r_ma3 = lag(dose_r_ma3, 1),
    lag_volume = lag(group.volume, 1)
  ) %>%
  ungroup() %>%  # Make sure there are no NAs in the first periods
  drop_na(lag_Delta_EDA_ma3_x, lag_deviation_f0, lag_dose_r_ma3)

pdata <- pdata.frame(pdata, index = c("entity_id", "period"))

gmm_model <- pgmm(log_returns ~ Delta_EDA_ma3.x + deviation_f0 + dose_r_ma3 + group.volume | 
                    lag_Delta_EDA_ma3_x + lag_deviation_f0 + lag_dose_r_ma3 + lag_volume,
                  data = pdata, effect = "individual", model = "twosteps")


# Check the model summary including Sargan/Hansen test
summary(gmm_model, diagnostics = TRUE)



### VAR analysis data_eda_agg
library(vars)

# List to store VAR models for each market
var_models <- list()

# List to store VAR models for each market
var_models <- list()

# Use a different variable for the loop to avoid conflict
unique_markets <- unique(data_agg_eda$market_id)

for(m_id in unique_markets) {
  # Subset the data for the current market and select only the specified variables
  market_data <- data_agg_eda %>%
    filter(market_id == m_id) %>%
    dplyr::select(period, avg_log_returns, avg_Delta_Mean_eda_ma3) %>%
    na.omit()  # Remove rows with NAs
  
  # Debugging: Print the number of rows in the subset to check it's correct
  print(paste("Market ID:", m_id, "Rows:", nrow(market_data)))
  
  # Convert to ts object without specifying frequency
  var_ts <- ts(market_data[, -1])  # Excluding 'period' column
  
  # Determine optimal number of lags using AIC
  lag_selection <- VARselect(var_ts, lag.max = 2, type = "both")
  optimal_lags <- lag_selection$selection["AIC(n)"]
  
  # Fit the VAR model
  var_models[[as.character(m_id)]] <- VAR(var_ts, p = optimal_lags, type = "both")
}
# To access the summary of the model for a specific market (e.g., market ID '4')
if("4" %in% names(var_models)) {
  print(summary(var_models[["4"]]))
} else {
  print("No model found for market 1.")
}

library(vars)

# Granger causality
granger_result_log_returns <- causality(var_models[["1"]], cause = "avg_Delta_Mean_eda_ma3")

# Test if avg_log_returns Granger-causes avg_Mean_eda
granger_result_Mean_eda <- causality(var_models[["1"]], cause = "avg_log_returns")

# Print the results
print(granger_result_log_returns)
print(granger_result_Mean_eda)




### Figure for EDA analysis
eda_summary <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/EDA_panel_June6.xlsx', sheet='Summary') # Rounds panel data from 2 hybrid markets

# If the data frame does not have an explicit row index, create one
eda_summary$Round <- seq_along(eda_summary[[1]])

# Rename the columns for easier referencing
names(eda_summary)[1:2] <- c("Avg_Price", "Tonic_EDA")

# Create the plot
p <- ggplot(data = eda_summary, aes(x = Round)) +
  geom_line(aes(y = Avg_Price, color = "blue")) + # Blue line for Average Price
  geom_line(aes(y = Tonic_EDA * max(Avg_Price) / max(Tonic_EDA), color = "red")) + # Red line for Tonic EDA
  scale_color_manual(values = c("blue" = "blue", "red" = "red")) +
  scale_y_continuous("Average price (5 markets)", 
                     sec.axis = sec_axis(~ . * max(eda_summary$Tonic_EDA) / max(eda_summary$Avg_Price), name = "Average tonic EDA activity (5 markets)")) +
  labs(x = "Period") +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white"), # Set panel background to white
        plot.background = element_rect(fill = "white", colour = "white"), # Ensure plot background is also white
        legend.position = "none") # Hide the legend if not needed

# Print the plot
print(p)

# Save the figure
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/price_eda_5markets.png", p, width = 12, height = 10, dpi = 300)

