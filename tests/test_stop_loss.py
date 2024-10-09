def test_load_max_profit():
    from stop_loss.stop_loss_main import load_max_profit,save_max_profit
    max_profit = None

    load_max_profit()
    save_max_profit()

    print(max_profit)

def test_save_max_profit():
    from stop_loss.stop_loss_main import save_max_profit
    save_max_profit()