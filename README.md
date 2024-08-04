# AnimeOut WinDecoder

**AnimeOut WinDecoder** is a Windows application designed for encoding and decoding directories of files. This tool supports operations like batch processing and recursive directory handling. It offers a graphical user interface with options for toggling features and visual feedback via button flashing.

## Features
- **Batch Encoding/Decoding:** Process multiple files or directories in one operation.
- **Recursive Processing:** Handle directories and subdirectories.
- **Checkbox Options:** Customize processing with various options.
- **Visual Feedback:** Buttons flash to indicate processing status.

## Getting Started

### Prerequisites

- Windows OS (Windows 7 or later recommended)
- If you are building from source: Microsoft Visual Studio or another C++ compiler that supports Windows API.

### Installation

Download the [latest release](https://github.com/s-vhs/AnimeOut-CommunityTools/releases/latest) and run the `AnimeOut-WinDecoder.exe`-file.

If you want to build from source, follow these steps:

1. **Clone the Repository:**
    ```bash 
    git clone https://github.com/yourusername/AnimeOut-WinDecoder.git
2. **Open the Project:** Open the project in Microsoft Visual Studio or another C++ IDE that supports Windows development.
3. **Build the Project:** Compile the project using your IDE's build tools. Ensure all dependencies are resolved.
4. **Run the Application:** Execute the compiled binary (`AnimeOut-WinDecoder.exe`) from your build output directory.

## Usage

1. **Load Directory Path:**
    - The application reads the directory path from a file named `FolderPath.txt` located in the Temp directory. This will be generated automatically.
2. **Select Options:**
    - **Recursive:** Process directories recursively.
    - **Rename Folders:** Optionally rename folders during processing.
3. **Encode/Decode:**
    - Click the **Encode!** or **Decode!** button to start processing the files in the specified directory.
4. Visual Feedback:
    - The button will flash three times to indicate that processing is occurring.

## Troubleshooting

- **Button Not Flashing:** Ensure there are no conflicting timers or visibility issues in the code. Verify that the `FlashButtonProc` function is correctly implemented.
- **File Not Found Error:** Confirm that `FolderPath.txt` exists in the Temp directory *and* contains the correct path.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

- **Fork the Repository**
- **Create a New Branch**
- **Commit Your Changes**
- **Push to Your Fork**
- **Create a Pull Request**

## License

This project is licensed under the GPL-3.0 license. See the [LICENSE](https://github.com/s-vhs/AnimeOut-CommunityTools/blob/master/LICENSE) file for details.

## Contact

For questions or issues, please contact:

- **Email:** bodenstein@vk.com
- **GitHub:** [@s-vhs](https://github.com/s-vhs)
- **Discord:** @ForsakenMaiden

## Acknowledgments

- Windows API documentation and resources.
- Microsoft Visual Studio development environment.