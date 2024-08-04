def myStrategy():
    if self.position.size == 0:
        # Buy everything
        self.place_order(price=self.dataclose[0], size=self.broker.get_cash() / self.dataclose[0], order_type='market', action='buy')
    else:
        self.place_order(price=self.dataclose[0], size=self.broker.get_cash() / self.dataclose[0], order_type='market', action='sell')
