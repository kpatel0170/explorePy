from turtle import Turtle
from pathlib import Path

ALIGNMENT = "center"
FONT = ("Arial", 20, "normal")
HIGH_SCORE_PATH = Path(__file__).with_name("high_score.txt")


class ScoreBoard(Turtle):
    def __init__(self):
        super().__init__()
        self.score = 0
        self.high_score = (
            int(HIGH_SCORE_PATH.read_text()) if HIGH_SCORE_PATH.exists() else 0
        )
        self.color("white")
        self.hideturtle()
        self.penup()
        self.goto(0, 270)
        self.update_scoreboard()

    def update_scoreboard(self):
        self.clear()
        self.write(
            f"Score : {self.score} , High Score : {self.high_score}",
            align=ALIGNMENT,
            font=FONT,
        )

    def increase_score(self):
        self.score += 1
        self.update_scoreboard()

    def reset_scoreboard(self):
        if self.score > self.high_score:
            self.high_score = self.score
            HIGH_SCORE_PATH.write_text(f"{self.high_score}")
        self.score = 0
        self.update_scoreboard()
