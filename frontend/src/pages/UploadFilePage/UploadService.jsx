import api from "../../services/api";


class UploadService {
  async uploadFiles(projectId, key, files) {
    try {
      const formData = new FormData();

      formData.append("projectId", projectId);
      formData.append("key", key);

      // Accept only actual File objects
      const realFiles = files.filter(f => f instanceof File);

      if (realFiles.length === 0) {
        console.warn(`Skipping upload for '${key}' because no real files found`);
        return { status: "skipped", uploaded: [] };
      }

      realFiles.forEach(file => {
        formData.append("files", file, file.name);
      });

      const response = await api.post("/projects/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });

      return response.data;

    } catch (err) {
      console.error("UploadService Error:", err);
      throw err;
    }
  }
}

export default new UploadService();
