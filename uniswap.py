import random
import math
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt

model_reporters = {
    "Price": lambda model: model.uniswap.get_price(),
    "External Price": lambda model: model.uniswap.external_price
}
agent_reporters={"eth": "eth", "dai": "dai"}

def transfer(from_agent, to_agent, currency, amount):
    from_amount = getattr(from_agent, currency, 0)
    to_amount = getattr(to_agent, currency, 0)
    setattr(from_agent, currency, from_amount - amount)
    setattr(to_agent, currency, to_amount + amount)

class Uniswap(Agent):
    def __init__(self, unique_id, model, dai, eth):
        super().__init__(unique_id, model)
        self.dai = dai
        self.eth = eth
        self.base_price = self.get_price()
        self.external_price = self.base_price

    def step(self):
        self.external_price = self.base_price * (1 + math.sin(0.1 * self.model.schedule.steps) / 10)

    def get_price(self):
        return self.dai / self.eth

    def trade(self, trader, currency, amount):
        if currency == "eth":
            eth_amount = self.eth - (self.eth * self.dai) / (self.dai + amount)
            transfer(trader, self, "dai", amount)
            transfer(self, trader, "eth", eth_amount)
        else:
            dai_amount = self.dai - (self.eth * self.dai) / (self.eth + amount)
            transfer(trader, self, "eth", amount)
            transfer(self, trader, "dai", dai_amount)

class Trader(Agent):
    def __init__(self, unique_id, model, eth, dai, is_arbitrageur):
        super().__init__(unique_id, model)
        self.eth = eth
        self.dai = dai
        self.is_arbitrageur = is_arbitrageur

    def buy_eth(self):
        amount = min(random.random() * 1000, self.dai)
        self.model.uniswap.trade(self, "eth", amount)

    def buy_dai(self):
        amount = min(random.random() * 10, self.eth)
        self.model.uniswap.trade(self, "dai", amount)

    def step(self):
        uniswap = self.model.uniswap
        if self.is_arbitrageur:
            if (uniswap.external_price > uniswap.get_price()):
                self.buy_eth()
            else:
                self.buy_dai()
        else:
            if random.random() > 0.5:
                self.buy_eth()
            else:
                self.buy_dai()

class UniswapModel(Model):
    def __init__(self, num_traders, num_arbitrageurs, trader_dai, trader_eth, uniswap_dai, uniswap_eth):
        super().__init__()
        self.num_traders = num_traders
        self.schedule = RandomActivation(self)
        self.uniswap = Uniswap(1, self, uniswap_dai, uniswap_eth)

        for i in range(num_traders):
            trader = Trader(i, self, trader_eth, trader_dai, i < num_arbitrageurs)
            self.schedule.add(trader)

        self.datacollector = DataCollector(model_reporters=model_reporters,agent_reporters=agent_reporters)

    def step(self):
        self.datacollector.collect(self)
        self.uniswap.step()
        self.schedule.step()

if __name__ == '__main__':
    num_traders =  100
    num_arbitrageurs = 10
    trader_dai =  10000
    trader_eth =  1000
    uniswap_dai =  1000000
    uniswap_eth =  10000

    model = UniswapModel(num_traders, num_arbitrageurs, trader_dai, trader_eth, uniswap_dai, uniswap_eth)
    for i in range(100):
        model.step()

    df = model.datacollector.get_model_vars_dataframe()
    df.plot()
    plt.show()
