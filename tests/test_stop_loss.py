def test_load_max_profit():
    from stop_loss.stop_loss_main import StopLossProgram
    program = StopLossProgram()
    program.load_max_profit()
    print(program.max_profit)

    # program.max_profit["515070.SH"] = 0.15
    # program.save_max_profit()
    program.load_max_profit()

    print(program.max_profit.get("515070.SH",3))

    print(program.max_profit)

