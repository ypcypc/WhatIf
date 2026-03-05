from runtime.game import GameEngine


class GameCLI:

    def __init__(self, engine: GameEngine):
        self.engine = engine
        self._streamed = False

    def run(self) -> None:
        self._print_banner()
        choice = self._prompt_start_menu()
        if choice == "new":
            opening = self.engine.new_game(on_chunk=self._on_chunk)
            self._print_narrative(opening)
        elif choice == "load":
            slot = self._select_save_slot()
            if slot is not None:
                message = self.engine.load_game(slot)
                print(f"\n{message}\n")
            else:
                opening = self.engine.new_game(on_chunk=self._on_chunk)
                self._print_narrative(opening)
        else:
            return

        self._game_loop()

    def _print_banner(self) -> None:
        print("\n" + "=" * 60)
        print("              WhatIf")
        print("=" * 60)
        print()

    def _prompt_start_menu(self) -> str:
        print("请选择：")
        print("  [1] 开始新游戏")
        print("  [2] 加载存档")
        print("  [3] 退出")
        print()

        while True:
            choice = input("请输入选项 (1/2/3): ").strip()
            if choice == "1":
                return "new"
            elif choice == "2":
                return "load"
            elif choice == "3":
                return "quit"
            else:
                print("无效选项，请重新输入")

    def _select_save_slot(self) -> int | None:
        saves = self.engine.list_saves()
        if not saves:
            print("\n没有找到存档，将开始新游戏")
            return None

        print()
        for save in saves:
            print(
                f"  [{save['slot']}] {save['description']} "
                f"- {save['save_time'][:19]}"
            )
        print()

        while True:
            slot_str = input("请输入槽位号（或按 Enter 取消）: ").strip()
            if not slot_str:
                return None
            try:
                slot = int(slot_str)
                if any(s["slot"] == slot for s in saves):
                    return slot
                else:
                    print(f"槽位 {slot} 不存在")
            except ValueError:
                print("请输入有效的数字")

    def _game_loop(self) -> None:
        while True:
            try:
                rs = self.engine.response_state
                if rs.game_ended:
                    break

                if rs.phase == "confrontation" and not rs.awaiting_next_event:
                    player_input = input("\n> ").strip()
                    if not player_input:
                        continue
                    if player_input.lower() in ("/quit", "/exit", "/q"):
                        self._handle_quit()
                        break

                    self.engine.on_narrative_chunk = self._on_chunk
                    response = self.engine.process_input(player_input)
                    self._print_narrative(response)
                else:
                    input()
                    response = self.engine.continue_game(on_chunk=self._on_chunk)
                    self._print_narrative(response)

                if self.engine.response_state.game_ended:
                    break

            except KeyboardInterrupt:
                print()
                self._handle_quit()
                break
            except Exception as e:
                print(f"\n[错误] {e}")
                raise

        if self.engine.response_state.game_ended:
            self.engine.shutdown()
            print("\n再见！")

    def _on_chunk(self, chunk: str) -> None:
        if not self._streamed:
            print()
            self._streamed = True
        print(chunk, end="", flush=True)

    def _print_narrative(self, text: str) -> None:
        if self._streamed:
            print("\n")
            self._streamed = False
            return
        print()
        paragraphs = text.split("\n\n")
        for p in paragraphs:
            print(p)
        print()

    def _handle_quit(self) -> None:
        if self.engine.current_event_id is not None:
            print("\n是否保存？(y/n)")
            choice = input().strip().lower()
            if choice == "y":
                self.engine.auto_save()
                print("已保存")

        self.engine.shutdown()
        print("\n再见！")
