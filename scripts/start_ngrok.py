from pyngrok import ngrok

# Add your auth token here
ngrok.set_auth_token("ngrok config add-authtoken 3E1pheKoNcL8tc8W4zkjN7EfXV8_3c2TfdRrL4M7XSBMhBysR")

# Start tunnel
public_url = ngrok.connect(5000)

print("Public URL:")
print(public_url)