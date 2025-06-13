import discord
from discord import app_commands
from discord.ext import commands
import subprocess
import os

class CodeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def runc(filename):
        dockerfile_content = """\
        FROM gcc:latest
        WORKDIR /app
        COPY . /app
        CMD ["bash"]
        """
        with open("Dockerfile", "w") as f:
            f.write(dockerfile_content)
          
        subprocess.run(["docker", "build", "-t", "c_sandbox", "."], check=True)


        subprocess.run(["docker", "run", "--rm", "-v", f"{os.getcwd()}:/app", "c_sandbox", "gcc", "-o", "program", filename], check=True)

        result = subprocess.run(["docker", "run", "--rm", "-v", f"{os.getcwd()}:/app", "c_sandbox", "./program"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        return result.stdout.strip()  

    code_group = app_commands.Group(name="code", description="All code-related commands.")

    @app_commands.choices(language=[
        app_commands.Choice(name="C", value="c"),
        app_commands.Choice(name="C++", value="cpp"),
        app_commands.Choice(name="Python", value="py")
    ])
    @code_group.command(name="compile", description="Compiles code.")
    @app_commands.default_permissions(manage_nicknames=True)
    async def compile(self, interaction: discord.Interaction, code: str = None, language: str):

        match language:
            case 'c':
                with open("code.c", "w") as f:
                    f.write(code)

                output = self.runc("code.c")

                embed = discord.Embed(
                    title="Compiling C code...",
                    description=output if output else "No output received.",
                    color=discord.Color.blue()
                )

                await interaction.response.send_message(embed=embed)

            case _:
                await interaction.response.send_message("Unsupported language!")

async def setup(bot):
    await bot.add_cog(CodeCog(bot))
